from app import db, app
from flask_marshmallow import Marshmallow
from enum import Enum
import jwt
import datetime

ma = Marshmallow(app)

# Define Coach and Client vars
class Role(Enum):
    COACH = 'COACH'
    CLIENT = 'CLIENT'


# Users table
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    approved = db.Column(db.Boolean, nullable=True)
    check_in = db.Column(db.Boolean, nullable=True)
    coach_id = db.Column(db.Integer, nullable=True)
    access_token = db.Column(db.String, nullable=True)
    role = db.Column(db.String, nullable=False)
    verification_token = db.Column(db.String, nullable=True)
    verified = db.Column(db.Boolean, nullable=False)
    reset_token = db.Column(db.String, nullable=True)
    
    # 1 to many relationship with Client_templates
    client_template = db.relationship('ClientTemplate', cascade="all, delete-orphan", lazy='dynamic')

    def encode_auth_token(self, sub):
        """
        Generates the Auth Token
        :sub: a dictionary containing any valid values
        :return: string
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=0, hours=2),
                'iat': datetime.datetime.utcnow(),
                'sub': sub
            }
            return jwt.encode(
                payload,
                app.config.get('SECRET_KEY'),
                algorithm='HS256'
            ).decode(encoding="utf-8")
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token
        :param auth_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'))
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Expired'
        except jwt.InvalidTokenError:
            return 'Invalid'

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'approved', 'check_in', 'coach_id', 'access_token', 'role', 'verification_token', 'verified', 'reset_token')

user_schema = UserSchema()
user_schemas = UserSchema(many=True)


# Coach_templates Table
class CoachTemplate(db.Model):
    __tablename__ = "Coach_templates"

    id = db.Column(db.Integer, primary_key=True)
    # 1 to many relationship with Coach_sessions table
    coach_sessions = db.relationship('CoachSession', cascade="all, delete-orphan", lazy='dynamic')

class CoachTemplateSchema(ma.Schema):
    class Meta:
        fields = ('id',)

coach_template_schema = CoachTemplateSchema()
coach_template_schemas = CoachTemplateSchema(many=True)


# Coach_sessions table
class CoachSession(db.Model):
    __tablename__ = "Coach_sessions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    # many to 1 relationship with Coach_templates table
    coach_template_id = db.Column(db.Integer, db.ForeignKey('Coach_templates.id'), nullable=False)
    # 1 to many relationship with Coach_exercises
    coach_exercises = db.relationship('CoachExercise', cascade="all, delete-orphan", lazy='dynamic')

class CoachSessionSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'order')

coach_session_schema = CoachSessionSchema()
coach_session_schemas = CoachSessionSchema(many=True)


# Coach_exercises table
class CoachExercise(db.Model):
    __tablename__ = "Coach_exercises"

    id = db.Column(db.Integer, primary_key=True)
    # 1 to 1 relationship with Exercises
    exercise_id = db.Column(db.Integer, db.ForeignKey('Exercises.id'), nullable=False)
    # many to 1 relationship with Coach_sessions table
    coach_session_id = db.Column(db.Integer, db.ForeignKey('Coach_sessions.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)  

class CoachExerciseSchema(ma.Schema):
    class Meta:
        fields = ('id', 'exercise_id', 'coach_session_id' 'order')

coach_exercise_schema = CoachExerciseSchema()
coach_exercise_schemas = CoachExerciseSchema(many=True)


# Exercises table
class Exercise(db.Model):
    __tablename__ = "Exercises"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    # 1 to 1 relationship with Coach_Exercises table
    coach_exercises = db.relationship('CoachExercise', cascade="all, delete-orphan", lazy=True, uselist=False)
    # 1 to 1 relationship with Training_entries table
    training_entries = db.relationship('TrainingEntry', cascade="all, delete-orphan", lazy=True, uselist=False)

class ExerciseSchema(ma.Schema):
    class Meta:
        fields = ('id', 'category', 'name')

exercise_schema = ExerciseSchema()
exercise_schemas = ExerciseSchema(many=True)


# Client_templates Table
class ClientTemplate(db.Model):
    __tablename__ = "Client_templates"

    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.String, nullable=False)
    end_date = db.Column(db.String, nullable=True)
    checkins = db.Column(db.String, nullable=False)
    # many to one relationship with Users table
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    completed = db.Column(db.Boolean, nullable=False)
    # one to many relationship with Client_sessions
    client_sessions = db.relationship('ClientSession', cascade="all, delete-orphan", lazy=True)
    # one to many relationship with Check_ins table
    check_ins = db.relationship('CheckIn', cascade="all, delete-orphan", lazy=True)
    

class ClientTemplateSchema(ma.Schema):
    class Meta:
        fields = ('id','start_date', 'end_date', 'checkins', 'user_id', 'completed')

client_template_schema = ClientTemplateSchema()
client_template_schemas = ClientTemplateSchema(many=True)


# Client_sessions Table
class ClientSession(db.Model):
    __tablename__ = "Client_sessions"

    id = db.Column(db.Integer, primary_key=True)
    client_weight = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    # many to one relationship with CLient_templates table
    client_template_id = db.Column(db.Integer, db.ForeignKey('Client_templates.id'), nullable=False)
    # one to many relationship with Client_exercises table
    client_exercises = db.relationship('ClientExercise', cascade="all, delete-orphan", lazy=True)
    # one to many relationship with Training_entries table
    training_entries = db.relationship('TrainingEntry', cascade="all, delete-orphan", lazy=True)

class ClientSessionSchema(ma.Schema):
    class Meta:
        fields = ('id','client_weight', 'comment', 'name', 'order', 'client_template_id')

client_session_schema = ClientSessionSchema()
client_session_schemas = ClientSessionSchema(many=True)



# Client_exercises Table
class ClientExercise(db.Model):
    __tablename__ = "Client_exercises"

    id = db.Column(db.Integer, primary_key=True)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight =db.Column(db.Integer, nullable=False)
    category = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    # many to one relationship with CLient_templates table
    client_session_id = db.Column(db.Integer, db.ForeignKey('Client_sessions.id'), nullable=False)


class ClientExerciseSchema(ma.Schema):
    class Meta:
        fields = ('id','sets', 'reps', 'weight', 'category', 'name', 'order', 'client_session_id')

client_exercise_schema = ClientExerciseSchema()
client_exercise_schemas = ClientExerciseSchema(many=True)



# Training_entries table
class TrainingEntry(db.Model):
    __tablename__ = "Training_entries"

    id = db.Column(db.Integer, primary_key=True)
    # many to one relationship with CLient_templates table
    client_session_id = db.Column(db.Integer, db.ForeignKey('Client_sessions.id'), nullable=False)
    # one to one relationship with Exercises table
    exercise_id = db.Column(db.Integer, db.ForeignKey('Exercises.id'), nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight =db.Column(db.Integer, nullable=False)


class TrainingEntrySchema(ma.Schema):
    class Meta:
        fields = ('id', 'client_session_id', 'exercise_id' 'sets', 'reps', 'weight')

training_entry_schema = TrainingEntrySchema()
training_entry_schemas = TrainingEntrySchema(many=True)



# Check_ins table
class CheckIn(db.Model):
    __tablename__ = "Check_ins"

    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.String, nullable=False)
    # many to one relationship with CLient_templates table
    client_template_id = db.Column(db.Integer, db.ForeignKey('Client_templates.id'), nullable=False)
    comment = db.Column(db.String, nullable=False)

   

class CheckInSchema(ma.Schema):
    class Meta:
        fields = ('id','time', 'client_template_id', 'comment')

check_in_schema = CheckInSchema()
check_in_schemas = CheckInSchema(many=True)