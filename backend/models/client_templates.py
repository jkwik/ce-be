from backend import db, app, ma
from backend.models.coach_templates import Exercise

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
