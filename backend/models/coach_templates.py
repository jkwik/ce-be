from backend import db, app, ma

# Exercises table
class Exercise(db.Model):
    __tablename__ = "Exercises"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    # 1 to 1 relationship with Coach_Exercises table

class ExerciseSchema(ma.Schema):
    class Meta:
        fields = ('id', 'category', 'name')

exercise_schema = ExerciseSchema()
exercise_schemas = ExerciseSchema(many=True)


# Coach_exercises table
class CoachExercise(db.Model):
    __tablename__ = "Coach_exercises"

    id = db.Column(db.Integer, primary_key=True)
    # 1 to 1 relationship with Exercises
    exercise_id = db.Column(db.Integer, db.ForeignKey('Exercises.id'), nullable=False)
    category = db.relationship(Exercise, lazy=True, uselist=False, single_parent=True, primaryjoin="Exercise.id==CoachExercise.exercise_id")
    name = db.relationship(Exercise, lazy=True, uselist=False, single_parent=True, primaryjoin="Exercise.id==CoachExercise.exercise_id")
    # many to 1 relationship with Coach_sessions table
    coach_session_id = db.Column(db.Integer, db.ForeignKey('Coach_sessions.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)  

class CoachExerciseSchema(ma.Schema):
    category = ma.Pluck('ExerciseSchema', 'category', many=False)
    name = ma.Pluck('ExerciseSchema', 'name', many=False)
    class Meta:
        fields = ('id', 'exercise_id', 'coach_session_id', 'order', 'category', 'name')

coach_exercise_schema = CoachExerciseSchema()
coach_exercise_schemas = CoachExerciseSchema(many=True)


# Coach_sessions table
class CoachSession(db.Model):
    __tablename__ = "Coach_sessions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    # many to 1 relationship with Coach_templates table
    coach_template_id = db.Column(db.Integer, db.ForeignKey('Coach_templates.id'), nullable=False)
    # 1 to many relationship with Coach_exercises
    coach_exercises = db.relationship('CoachExercise', cascade="all, delete-orphan", lazy=True, order_by="CoachExercise.order")

class CoachSessionSchema(ma.Schema):
    coach_exercises = ma.Nested(CoachExerciseSchema, many=True)
    class Meta:
        fields = ('id', 'name', 'order', 'coach_template_id', 'coach_exercises')

coach_session_schema = CoachSessionSchema()
coach_session_schemas = CoachSessionSchema(many=True)

# this schema is used for retrieving partial information about a session
class PartialCoachSessionSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'order')



# Coach_templates Table
class CoachTemplate(db.Model):
    __tablename__ = "Coach_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, primary_key=True)
    # 1 to many relationship with Coach_sessions table
    sessions = db.relationship('CoachSession', cascade="all, delete-orphan", lazy=True, order_by="CoachSession.order")

class CoachTemplateSchema(ma.Schema):
    sessions = ma.Nested(PartialCoachSessionSchema, many=True)
    class Meta:
        fields = ('id', 'name', 'sessions')

coach_template_schema = CoachTemplateSchema()
coach_template_schemas = CoachTemplateSchema(many=True)
