from backend import db, app, ma

# Coach_templates Table
class CoachTemplate(db.Model):
    __tablename__ = "Coach_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, primary_key=True)
    # 1 to many relationship with Coach_sessions table
    coach_sessions = db.relationship('CoachSession', cascade="all, delete-orphan", lazy='dynamic')

class CoachTemplateSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name')

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
