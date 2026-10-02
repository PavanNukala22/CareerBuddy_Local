from django.db import migrations


# Old (pre-redesign) text — used for reverse().
OLD_SUB_DESC = ("Students play bingo with common business buzzwords and idioms, "
                "marking words as they hear them.")
OLD_SUB_INSTR = ("1. Your bingo card contains 25 common business buzzwords.\n"
                 "2. The instructor reads definitions — mark the word when you hear its definition.\n"
                 "3. Get 5 in a row (horizontally, vertically, or diagonally) to call BINGO!\n"
                 "4. You must define any marked word correctly to claim your square.")
OLD_EX_INSTR = ("Click 'Start Game', then click words on the bingo card when their "
                "definition is read aloud. Get 5 in a row to win!")

# New text — matches the current "definition -> word" gameplay.
NEW_SUB_DESC = ("Students match spoken definitions to the correct business buzzword "
                "on a 25-word card.")
NEW_SUB_INSTR = ("1. Your card contains 25 common business buzzwords.\n"
                 "2. Press Start. For each round a definition is shown and read aloud — "
                 "the word itself is hidden.\n"
                 "3. Click the word that matches the definition (your pick turns blue). "
                 "You must pick a word before moving on.\n"
                 "4. After the last word, every pick is graded — green for correct, "
                 "red for incorrect — and your score is shown.")
NEW_EX_INSTR = ("Press 'Start Game'. Read/listen to each definition and click the word "
                "that matches it, then click 'Next Word'. Your picks are graded at the "
                "end and your score is shown.")


def _apply(apps, sub_desc, sub_instr, ex_instr):
    SubActivity = apps.get_model("activities", "SubActivity")
    Exercise = apps.get_model("activities", "Exercise")

    SubActivity.objects.filter(title="Buzzword Bingo").update(
        description=sub_desc, instructions=sub_instr
    )
    Exercise.objects.filter(exercise_type="bingo", title="Business Buzzword Bingo").update(
        instructions=ex_instr
    )


def forwards(apps, schema_editor):
    _apply(apps, NEW_SUB_DESC, NEW_SUB_INSTR, NEW_EX_INSTR)


def backwards(apps, schema_editor):
    _apply(apps, OLD_SUB_DESC, OLD_SUB_INSTR, OLD_EX_INSTR)


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0005_alter_freeactivityselection_user_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
