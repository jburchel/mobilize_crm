from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship, declarative_base, scoped_session, sessionmaker
from contextlib import contextmanager
from marshmallow import Schema, fields, validate, ValidationError

Base = declarative_base()

class PersonSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(allow_none=True)
    phone = fields.Str(validate=validate.Regexp(r'^\+?1?\d{9,15}$'))
    address = fields.Str(allow_none=True)
    role = fields.Str(validate=validate.OneOf(['admin', 'user', 'guest', 'Contact']))
    church_id = fields.Int(allow_none=True)
    google_resource_name = fields.Str(allow_none=True)

class ChurchSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    location = fields.Str(allow_none=True)
    phone = fields.Str(validate=validate.Regexp(r'^\+?1?\d{9,15}$'))
    email = fields.Email(allow_none=True)
    main_contact_id = fields.Int(allow_none=True)

class TaskSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    due_date = fields.Date(allow_none=True)
    priority = fields.Str(validate=validate.OneOf(['Low', 'Medium', 'High']))
    status = fields.Str(required=True, validate=validate.OneOf(['Not Started', 'In Progress', 'Completed']))
    person_id = fields.Int(allow_none=True)
    church_id = fields.Int(allow_none=True)

class CommunicationSchema(Schema):
    id = fields.Int(dump_only=True)
    comm_type = fields.Str(required=True, validate=validate.OneOf(['Email', 'SMS', 'Phone', 'Letter']))
    message = fields.Str(required=True)
    date_sent = fields.Date(required=True)
    person_id = fields.Int(allow_none=True)
    church_id = fields.Int(allow_none=True)

# Initialize schemas
person_schema = PersonSchema()
church_schema = ChurchSchema()
task_schema = TaskSchema()
communication_schema = CommunicationSchema()

class Person(Base):
    __tablename__ = 'people'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    address = Column(String)
    church_id = Column(Integer, ForeignKey('churches.id'))
    role = Column(String)
    google_resource_name = Column(String, unique=True, nullable=True)

    church = relationship("Church", back_populates="people", foreign_keys=[church_id])
    tasks = relationship("Task", back_populates="person")
    communications = relationship("Communication", back_populates="person")

    def __repr__(self):
        return f"<Person(name='{self.name}', email='{self.email}')>"

class Church(Base):
    __tablename__ = 'churches'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)
    phone = Column(String)
    email = Column(String)
    main_contact_id = Column(Integer, ForeignKey('people.id'))

    people = relationship("Person", back_populates="church", foreign_keys=[Person.church_id])
    tasks = relationship("Task", back_populates="church")
    communications = relationship("Communication", back_populates="church")
    main_contact = relationship("Person", foreign_keys=[main_contact_id], backref="churches_main_contact")

    def __repr__(self):
        return f"<Church(name='{self.name}', location='{self.location}')>"

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    due_date = Column(Date)
    priority = Column(String)
    status = Column(String)
    person_id = Column(Integer, ForeignKey('people.id'))
    church_id = Column(Integer, ForeignKey('churches.id'))

    person = relationship("Person", back_populates="tasks")
    church = relationship("Church", back_populates="tasks")

    def __repr__(self):
        return f"<Task(title='{self.title}', due_date='{self.due_date}')>"

class Communication(Base):
    __tablename__ = 'communications'

    id = Column(Integer, primary_key=True)
    type = Column(String)
    message = Column(String)
    date_sent = Column(Date)
    person_id = Column(Integer, ForeignKey('people.id'))
    church_id = Column(Integer, ForeignKey('churches.id'))

    person = relationship("Person", back_populates="communications")
    church = relationship("Church", back_populates="communications")

    def __repr__(self):
        return f"<Communication(type='{self.type}', date_sent='{self.date_sent}')>"

engine = create_engine('sqlite:///mobilize_crm.db')
Base.metadata.create_all(engine)

# Create a scoped session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
