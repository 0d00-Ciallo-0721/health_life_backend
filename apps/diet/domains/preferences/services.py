from apps.diet.models import UserPreference

class PreferenceService:
    @staticmethod
    def toggle_preference(user, target_id, target_type, action_cmd):
        """
        action_cmd: 'favorite', 'unfavorite', 'block', 'unblock'
        """
        db_action = 'like'
        is_delete = False
        
        if action_cmd in ['favorite', 'like']:
            db_action = 'like'
        elif action_cmd in ['unfavorite', 'unlike']:
            db_action = 'like'; is_delete = True
        elif action_cmd in ['block']:
            db_action = 'block'
        elif action_cmd in ['unblock']:
            db_action = 'block'; is_delete = True
        else:
            return False

        if is_delete:
            UserPreference.objects.filter(
                user=user, target_id=target_id, target_type=target_type, action=db_action
            ).delete()
            return "removed"
        else:
            UserPreference.objects.get_or_create(
                user=user, target_id=target_id, target_type=target_type, action=db_action
            )
            return "added"