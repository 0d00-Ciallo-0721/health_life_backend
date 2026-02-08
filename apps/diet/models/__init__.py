from .mysql.pantry import FridgeItem
from .mysql.journal import DailyIntake, WorkoutRecord, WeightRecord
from .mysql.preference import UserPreference
# [新增]
from .mysql.gamification import ChallengeTask, Remedy

from .mongo.recipe import Recipe
from .mongo.restaurant import Restaurant