from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("diet", "0005_remove_waterintake_cups_waterintake_food_ml_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userpreference",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("recipe", "菜谱"),
                    ("restaurant", "餐厅"),
                    ("feed", "动态"),
                    ("remedy", "补救方案"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="userpreference",
            name="action",
            field=models.CharField(
                choices=[
                    ("like", "收藏/喜欢"),
                    ("block", "拉黑/不吃"),
                    ("save", "保存"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="userpreference",
            unique_together={("user", "target_id", "target_type", "action")},
        ),
    ]
