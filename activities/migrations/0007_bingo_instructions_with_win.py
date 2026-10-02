from django.db import migrations


# Text from migration 0006 (definition->word, no bingo goal) — for reverse().
PREV_SUB_DESC = ("Students match spoken definitions to the correct business buzzword "
                 "on a 25-word card.")
PREV_SUB_INSTR = ("1. Your card contains 25 common business buzzwords.\n"
                  "2. Press Start. For each round a definition is shown and read aloud — "
                  "the word itself is hidden.\n"
                  "3. Click the word that matches the definition (your pick turns blue). "
                  "You must pick a word before moving on.\n"
                  "4. After the last word, every pick is graded — green for correct, "
                  "red for incorrect — and your score is shown.")
PREV_EX_INSTR = ("Press 'Start Game'. Read/listen to each definition and click the word "
                 "that matches it, then click 'Next Word'. Your picks are graded at the "
                 "end and your score is shown.")

# New text — restores the 5-in-a-row bingo goal.
NEW_SUB_DESC = ("Students match spoken definitions to the correct business buzzword "
                "on a 5×5 card and aim for a bingo.")
NEW_SUB_INSTR = ("1. Your card is a 5×5 grid of 25 business buzzwords.\n"
                 "2. Press Start. For each round a definition is shown and read aloud — "
                 "the word itself is hidden.\n"
                 "3. Click the word that matches the definition (your pick turns blue). "
                 "You must pick a word before moving on.\n"
                 "4. After the last word, every pick is graded — green for correct, "
                 "red for incorrect — and your score is shown.\n"
                 "5. Get 5 correct answers in a row, column, or diagonal to score a BINGO!")
NEW_EX_INSTR = ("Press 'Start Game'. Read/listen to each definition and click the matching "
                "word, then 'Next Word'. Correct answers fill your 5×5 card — get 5 in "
                "a row, column, or diagonal for a BINGO! Picks are graded at the end and "
                "your score is shown.")


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
    _apply(apps, PREV_SUB_DESC, PREV_SUB_INSTR, PREV_EX_INSTR)


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0006_update_buzzword_bingo_instructions"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
