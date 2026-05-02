from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("diet", "0006_expand_userpreference_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="remedy",
            name="points_cost",
            field=models.IntegerField(default=10, verbose_name="鎵ｉ櫎绉垎"),
        ),
        migrations.AlterField(
            model_name="remedy",
            name="scenario",
            field=models.CharField(
                choices=[
                    ("overeat", "鏆撮"),
                    ("stay_up", "鐔"),
                    ("miss_workout", "缂轰箯杩愬姩"),
                    ("low_water", "楗按涓嶈冻"),
                    ("constipation", "渚跨"),
                    ("hangover", "瀹块唹"),
                ],
                db_index=True,
                max_length=32,
                verbose_name="鍦烘櫙",
            ),
        ),
    ]
