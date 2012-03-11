""" Database Definitions
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship as Relationship
from sqlalchemy.schema import Column
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import Index
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.types import Date
from sqlalchemy.types import DateTime
from sqlalchemy.types import Enum
from sqlalchemy.types import Numeric
from sqlalchemy.types import Integer
from sqlalchemy.types import Unicode
from zope.interface import implements

from occams.datastore.interfaces import IEntity
from occams.datastore.interfaces import IValue
from occams.datastore.model._meta import Model
from occams.datastore.model._meta import Referenceable
from occams.datastore.model._meta import Describeable
from occams.datastore.model.tracking import Modifiable
from occams.datastore.model.tracking import buildModifiableConstraints
from occams.datastore.model.schema import Schema
from occams.datastore.model.schema import Attribute
from occams.datastore.model.schema import Choice


ENTITY_STATE_NAMES = sorted([term.token for term in IEntity['state'].vocabulary])


def _defaultCollectDate(context):
    """
    Callback for generating default collect date value.
    It will try to lookup the previous ``collect_date`` and give the
    date the entry is input by default if none is found.
    This method should not be called if one is supplied by the user.
    """
    entity_table = Entity.__table__
    name = context.current_parameters['name']
    collect_date = date.today()
    if name:
        result = context.connection.execute(
            select([entity_table.c.collect_date], (entity_table.c.name == name))
            .order_by(entity_table.c.create_date.desc())
            .limit(1)
            )
        previous = result.first()
        if previous:
            collect_date = previous.collect_date
    return collect_date


class Entity(Model, Referenceable, Describeable, Modifiable):
    implements(IEntity)

    schema_id = Column(ForeignKey(Schema.id, ondelete='CASCADE'), nullable=False)

    schema = Relationship('Schema')

    state = Column(
        Enum(*ENTITY_STATE_NAMES, name='entity_state'),
        nullable=False,
        server_default=IEntity['state'].default
        )

    collect_date = Column(Date, nullable=False, default=_defaultCollectDate)

    integer_values = Relationship('ValueInteger')

    datetime_values = Relationship('ValueDatetime')

    decimal_values = Relationship('ValueDecimal')

    string_values = Relationship('ValueString')

    obect_values = Relationship('ValueObject')

    @declared_attr
    def __table_args__(cls):
        return buildModifiableConstraints(cls) + (
            UniqueConstraint('schema_id', 'name'),
            Index('ix_%s_schema_id' % cls.__tablename__, 'schema_id'),
            Index('ix_%s_collect_date' % cls.__tablename__, 'collect_date'),
            )


class _ValueBaseMixin(Referenceable, Modifiable):
    implements(IValue)

    __valuetype__ = None

    @declared_attr
    def entity_id(cls):
        return Column(ForeignKey(Entity.id, ondelete='CASCADE'), nullable=False,)

    @declared_attr
    def entity(cls):
        return Relationship('Entity', primaryjoin='%s.entity_id == Entity.id' % cls.__name__)

    @declared_attr
    def attribute_id(cls):
        return Column(ForeignKey(Attribute.id, ondelete='CASCADE'), nullable=False,)

    @declared_attr
    def attribute(cls):
        return Relationship('Attribute')

    @declared_attr
    def choice_id(cls):
        return Column(ForeignKey(Choice.id, ondelete='CASCADE'),)

    @declared_attr
    def choice(cls):
        return Relationship('Choice')

    @declared_attr
    def _value(cls):
        return Column('value', cls.__valuetype__, index=True)

    @property
    def value(self):
        return self._value

    @declared_attr
    def __table_args__(cls):
        return buildModifiableConstraints(cls) + (
            Index('ix_%s_entity_id' % cls.__tablename__, 'entity_id'),
            Index('ix_%s_attribute_id' % cls.__tablename__, 'attribute_id'),
            Index('ix_%s_choice_id' % cls.__tablename__, 'choice_id'),
            )


class ValueDatetime(Model, _ValueBaseMixin):
    """
    A datetime EAV value.
    """

    __tablename__ = 'datetime'
    __valuetype__ = DateTime

    @property
    def value(self):
        return self._value if self.attribute.type == 'datetime' else self._value.date()


class ValueInteger(Model, _ValueBaseMixin):
    """
    A integer EAV value.
    """

    __tablename__ = 'integer'
    __valuetype__ = Integer

    @property
    def value(self):
        return self._value if self.attribute.type == 'integer' else bool(self._value)


class ValueDecimal(Model, _ValueBaseMixin):
    """
    A decimal EAV value.
    """

    __tablename__ = 'decimal'
    __valuetype__ = Numeric


class ValueString(Model, _ValueBaseMixin):
    """
    A string EAV value.
    """

    __tablename__ = 'string'
    __valuetype__ = Unicode


class ValueObject(Model, _ValueBaseMixin):
    """
    An object EAV value.
    """

    __tablename__ = 'object'
    __valuetype__ = ForeignKey(Entity.id, ondelete='CASCADE')

    # NOTE: If there are shared objects, THEY WILL BE REMOVED AS WELL...
    @declared_attr
    def value_object(cls):
        return Relationship('Entity', primaryjoin='%s.value == Entity.id' % cls.__name__,)

    @property
    def value(self):
        return self.value_object
