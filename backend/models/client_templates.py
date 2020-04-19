from backend import db, app, ma
from backend.models.coach_templates import Exercise

# Training_entries table
class TrainingEntry(db.Model):
    __tablename__ = "Training_entries"

    id = db.Column(db.Integer, primary_key=True)
    # many to one relationship with CLient_templates table
    client_session_id = db.Column(db.Integer, db.ForeignKey('Client_sessions.id'), nullable=False)
    # one to one relationship with Exercises table
    name = db.Column(db.String, nullable=False)
    category = db.Column(db.String, nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    order = db.Column(db.Integer, nullable=False)


class TrainingEntrySchema(ma.Schema):
    class Meta:
        fields = ('id', 'client_session_id', 'name', 'category', 'sets', 'reps', 'weight', 'order')

training_entry_schema = TrainingEntrySchema()
training_entry_schemas = TrainingEntrySchema(many=True)

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

# Client_sessions Table
class ClientSession(db.Model):
    __tablename__ = "Client_sessions"

    id = db.Column(db.Integer, primary_key=True)
    client_weight = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.String, nullable=True)
    name = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, nullable=False)
    # many to one relationship with CLient_templates table
    client_template_id = db.Column(db.Integer, db.ForeignKey('Client_templates.id'), nullable=False)
    # one to many relationship with Client_exercises table
    exercises = db.relationship('ClientExercise', cascade="all, delete-orphan", lazy=True, order_by="ClientExercise.order")
    # one to many relationship with Training_entries table
    training_entries = db.relationship('TrainingEntry', cascade="all, delete-orphan", lazy=True, order_by="TrainingEntry.order")
    completed_date = db.Column(db.String, nullable=True)


class ClientSessionSchema(ma.Schema):
    exercises = ma.Nested(ClientExerciseSchema, many=True)
    training_entries = ma.Nested(TrainingEntrySchema, many=True)
    class Meta:
        fields = ('id','client_weight', 'comment', 'name', 'slug', 'order', 'completed', 'client_template_id', 'exercises', 'training_entries', 'completed_date')

client_session_schema = ClientSessionSchema()
client_session_schemas = ClientSessionSchema(many=True)

# This schema is used to for the templates to pull partial information about sessions
class PartialClientSessionSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'slug', 'order', 'completed')

# Client_templates Table
class ClientTemplate(db.Model):
    __tablename__ = "Client_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, nullable=False)
    start_date = db.Column(db.String, nullable=False)
    end_date = db.Column(db.String, nullable=True)
    # many to one relationship with Users table
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', lazy=True, uselist=False, single_parent=True, primaryjoin="User.id==ClientTemplate.user_id")
    completed = db.Column(db.Boolean, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    # one to many relationship with Client_sessions
    sessions = db.relationship('ClientSession', cascade="all, delete-orphan", lazy=True, order_by="ClientSession.order")
    # one to many relationship with Check_ins table
    check_ins = db.relationship('CheckIn', cascade="all, delete-orphan", lazy=True)

# This partial user schema is used in retrieving templates
class PartialUserSchema(ma.Schema):
    class Meta:
        fields = ('first_name', 'last_name', 'email')

class ClientTemplateSchema(ma.Schema):
    sessions = ma.Nested(PartialClientSessionSchema, many=True)
    user = ma.Nested(PartialUserSchema, many=False)
    class Meta:
        fields = ('id', 'name', 'slug', 'start_date', 'end_date', 'user_id', 'completed', 'sessions', 'user', 'active')

client_template_schema = ClientTemplateSchema()
client_template_schemas = ClientTemplateSchema(many=True)

# Check_ins table
class CheckIn(db.Model):
    __tablename__ = "Check_ins"

    id = db.Column(db.Integer, primary_key=True)
    # many to one relationship with CLient_templates table
    client_template_id = db.Column(db.Integer, db.ForeignKey('Client_templates.id'), nullable=False)
    coach_comment = db.Column(db.String, nullable=False)
    client_comment = db.Column(db.String, nullable=False)
    start_date = db.Column(db.String, nullable=False)
    end_date = db.Column(db.String, nullable=False)
    completed = db.Column(db.Boolean, nullable=False)



class CheckInSchema(ma.Schema):
    class Meta:
        fields = ('id', 'client_template_id', 'coach_comment', 'client_comment', 'start_date', 'end_date', 'completed')

check_in_schema = CheckInSchema()
check_in_schemas = CheckInSchema(many=True) 
