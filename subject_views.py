import mimetypes
import re
from html import escape
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required

# Grammar lesson media lives OUTSIDE static/ on purpose. Under static/ these
# files would also be served publicly at /static/... , unauthenticated, which
# would defeat the @login_required on the views below and re-expose the licensed
# videos we moved in-house. From here they are reachable only through the
# login-gated subject_slide_image / subject_video views.
PROTECTED_MEDIA_DIR = settings.BASE_DIR / 'protected_media'
# Real presentation decks per topic, shown as the Visual Guide instead of the
# generated SVG slides. Each topic keeps its images under a slug-named folder.
SUBJECT_SLIDES_DIR = PROTECTED_MEDIA_DIR / 'subjectslides'
# Locally hosted lesson videos, one <slug>.mp4 per topic. These replace the
# YouTube embeds so the Video Lesson no longer depends on third-party clips
# (GRM: YouTube licensing concern).
SUBJECT_VIDEOS_DIR = PROTECTED_MEDIA_DIR / 'subjectvideos'
NOUN_VIDEO_EMBED_URL = (
    'https://www.youtube-nocookie.com/embed/LG9-dgwEXCo'
    '?rel=0&modestbranding=1&playsinline=1'
)
DEFAULT_SUBJECT_VIDEO_EMBED_URL = NOUN_VIDEO_EMBED_URL
TopicData = dict[str, Any]
SlideData = dict[str, Any]

SUBJECT_TOPIC_CARDS = [
    {
        'slug': 'noun',
        'title': 'Nouns',
        'description': 'Learn about common, proper, singular, plural, possessive, abstract, collective, and compound nouns.',
        'badge': 'N',
        'accent_color': '#3f7451',
        'card_class': 'card-blue',
    },
    {
        'slug': 'pronoun',
        'title': 'Pronouns',
        'description': 'Master personal, possessive, reflexive, demonstrative, interrogative, relative, and indefinite pronouns.',
        'badge': 'P',
        'accent_color': '#6b5b95',
        'card_class': 'card-pink',
    },
    {
        'slug': 'verb',
        'title': 'Verbs',
        'description': 'Understand action, linking, auxiliary, modal, transitive, intransitive, and phrasal verbs.',
        'badge': 'V',
        'accent_color': '#2f7a65',
        'card_class': 'card-mint',
    },
    {
        'slug': 'adjective',
        'title': 'Adjectives',
        'description': 'Explore descriptive, quantitative, demonstrative, possessive adjectives and degrees of comparison.',
        'badge': 'Adj',
        'accent_color': '#b56a3b',
        'card_class': 'card-peach',
    },
    {
        'slug': 'adverb',
        'title': 'Adverbs',
        'description': 'Study adverbs of manner, time, place, frequency, degree and their usual sentence positions.',
        'badge': 'Adv',
        'accent_color': '#a67c2e',
        'card_class': 'card-cream',
    },
    {
        'slug': 'conjunction',
        'title': 'Conjunctions',
        'description': 'Master coordinating, subordinating, correlative conjunctions and conjunctive adverbs.',
        'badge': 'Conj',
        'accent_color': '#5d698f',
        'card_class': 'card-lilac',
    },
    {
        'slug': 'tenses',
        'title': 'Tenses',
        'description': 'Learn all 12 tenses: simple, continuous, perfect, and perfect continuous forms.',
        'badge': 'T',
        'accent_color': '#3f6f8f',
        'card_class': 'card-cyan',
    },
    {
        'slug': 'sentence-structure',
        'title': 'Sentence Structure',
        'description': 'Understand phrases, clauses, sentence patterns and common sentence-building errors.',
        'badge': 'S',
        'accent_color': '#7a4f59',
        'card_class': 'card-rose',
    },
    {
        'slug': 'types-of-sentences',
        'title': 'Types of Sentences',
        'description': 'Master declarative, interrogative, imperative, and exclamatory sentences with examples.',
        'badge': 'TS',
        'accent_color': '#5a5f7a',
        'card_class': 'card-violet',
    },
]

SUBJECT_TOPICS = {
    'noun': {
        'slug': 'noun',
        'title': 'Nouns',
        'subtitle': 'Complete Guide with Types, Rules & Exercises',
        'badge': 'N',
        'accent_color': '#3f7451',
        'definition': (
            'A noun is a naming word. It names a person, place, thing, idea, feeling, or quality, '
            'and it helps us identify what a sentence is talking about.'
        ),
        'role_items': [
            'Name people, animals, places, objects, and ideas.',
            'Work as subjects, objects, complements, and objects of prepositions.',
            'Show number, possession, and classification.',
            'Build the core meaning of most English sentences.',
        ],
        'summary_rows': [
            ['Common Noun', 'General name for a class of people, places, or things', 'teacher, city, river'],
            ['Proper Noun', 'Specific name of a person, place, or thing', 'Anita, Delhi, the Nile'],
            ['Concrete Noun', 'Something you can sense physically', 'book, apple, bell'],
            ['Abstract Noun', 'An idea, quality, or feeling', 'honesty, courage, joy'],
            ['Collective Noun', 'A group seen as one unit', 'team, flock, jury'],
            ['Compound Noun', 'Two or more words acting as one noun', 'toothpaste, bus stop, mother-in-law'],
        ],
        'slides': [
            {
                'title': 'Spot the Naming Words',
                'lines': [
                    'Riya carried a basket to the market.',
                    'Riya, basket, and market are nouns.',
                    'Nouns tell us who or what the sentence is about.',
                ],
            },
            {
                'title': 'Kinds of Nouns',
                'lines': [
                    'Girl is a common noun, but Priya is a proper noun.',
                    'Table is concrete, but kindness is abstract.',
                    'Class and bouquet are collective nouns.',
                ],
            },
            {
                'title': 'How Nouns Work',
                'lines': [
                    'The cat slept. Noun as subject.',
                    'We fed the cat. Noun as object.',
                    'The bag is Rani\'s. Noun showing possession.',
                ],
            },
        ],
        'video_title': 'Nouns — Explained Simply',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/8m4SUIisdO0?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Nouns are names for people, places, things, and ideas.',
            'Identify common vs. proper nouns (e.g., city vs. London).',
            'Learn to use singular, plural, and possessive noun forms correctly.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main noun rules.',
        'audio_text': (
            'Nouns are naming words. They identify people, places, things, ideas, and feelings. '
            'Common nouns are general, like teacher or city, while proper nouns are specific, like Anita or Delhi. '
            'Nouns also change form to show more than one thing or to show that something belongs to someone.'
        ),
        'sections': [
            {
                'heading': 'What Nouns Name',
                'lead': (
                    'Nouns identify the people, places, things, and ideas we talk about. '
                    'Without nouns, our sentences would have action but no clear subject matter.'
                ),
                'table_headers': ['What It Names', 'Explanation', 'Examples'],
                'table_rows': [
                    ['Person', 'A human being or character', 'doctor, Meera, child'],
                    ['Place', 'A location or area', 'school, beach, Chennai'],
                    ['Thing', 'An object, animal, or material item', 'chair, tiger, pencil'],
                    ['Idea or Quality', 'Something you cannot touch but can think about', 'truth, freedom, anger'],
                ],
                'example_items': [
                    'Meera visited the museum on Sunday.',
                    'The puppy chewed my slipper.',
                    'Honesty builds trust in every friendship.',
                ],
            },
            {
                'heading': 'Major Types of Nouns',
                'lead': (
                    'English grammar groups nouns by the kind of name they give. '
                    'Learning these types helps you choose correct capitalization, articles, and agreement.'
                ),
                'category_items': [
                    {'label': 'Common Nouns', 'text': 'General names such as city, book, teacher, or flower.'},
                    {'label': 'Proper Nouns', 'text': 'Special names such as India, Ravi, or the Himalayas.'},
                    {'label': 'Abstract Nouns', 'text': 'Ideas and qualities such as love, bravery, and wisdom.'},
                    {'label': 'Collective Nouns', 'text': 'Group names such as class, crowd, and bunch.'},
                ],
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'Capitalize proper nouns because they name specific people, places, or things.'},
                    {'title': 'RULE 2', 'text': 'Do not capitalize common nouns unless they begin a sentence or are part of a title.'},
                    {'title': 'RULE 3', 'text': 'An abstract noun names something felt or understood, not something seen or touched.'},
                ],
                'example_items': [
                    'river is common, but Ganga is proper.',
                    'beauty and patience are abstract nouns.',
                    'A team entered the stadium together.',
                ],
            },
            {
                'heading': 'Number, Possession, and Compound Forms',
                'lead': 'Nouns change form to show one or many, ownership, or a combined name made from two words.',
                'table_headers': ['Grammar Feature', 'Rule', 'Examples'],
                'table_rows': [
                    ['Singular and Plural', 'Add -s or -es in many cases; some nouns change irregularly', 'book/books, child/children'],
                    ['Possessive', 'Add apostrophe plus s for ownership in most singular nouns', 'Riya\'s bag, the cat\'s tail'],
                    ['Plural Possessive', 'Add apostrophe after the plural noun ending in s', 'students\' notebooks'],
                    ['Compound Noun', 'Two or more words together name one thing', 'bedroom, washing machine, sister-in-law'],
                ],
                'example_items': [
                    'One box, two boxes.',
                    'The children\'s toys were on the floor.',
                    'My grandfather fixed the washing machine.',
                ],
            },
            {
                'heading': 'Functions of Nouns in Sentences',
                'lead': (
                    'Nouns can do different jobs in a sentence. '
                    'Recognizing their function makes sentence analysis easier and improves writing accuracy.'
                ),
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'A subject noun tells who or what performs the action: Birds sing.'},
                    {'title': 'RULE 2', 'text': 'An object noun receives the action: We watched the birds.'},
                    {'title': 'RULE 3', 'text': 'A noun can follow a preposition: The keys are on the table.'},
                ],
                'example_items': [
                    'The teacher explained the lesson clearly.',
                    'We visited the library after school.',
                    'The flowers in the vase look fresh.',
                ],
                'exercises': [
                    {'question': 'Q1. Identify the noun: The baby laughed loudly.', 'answer': 'baby'},
                    {'question': 'Q2. Change to plural: leaf', 'answer': 'leaves'},
                    {'question': 'Q3. Make this possessive: the bag of Rani', 'answer': 'Rani\'s bag'},
                ],
            },
        ],
    },
    'pronoun': {
        'slug': 'pronoun',
        'title': 'Pronouns',
        'subtitle': 'Complete Guide with Types, Rules & Exercises',
        'badge': 'P',
        'accent_color': '#6b5b95',
        'definition': (
            'A pronoun is a word used in place of a noun or noun phrase. Pronouns help us avoid repetition, '
            'make sentences smoother, and show the relationship between speakers, listeners, and things.'
        ),
        'role_items': [
            'Replace repeated nouns in a sentence or paragraph.',
            'Show person, number, gender, and ownership.',
            'Help form questions, comparisons, and relative clauses.',
            'Make speech and writing more natural and less repetitive.',
        ],
        'summary_rows': [
            ['Personal Pronoun', 'Refers to speaker, listener, or others', 'I, you, he, they'],
            ['Possessive Pronoun', 'Shows ownership', 'mine, ours, hers'],
            ['Reflexive Pronoun', 'Reflects back to the subject', 'myself, yourself, themselves'],
            ['Demonstrative Pronoun', 'Points to specific things', 'this, that, these, those'],
            ['Interrogative Pronoun', 'Asks questions', 'who, whom, whose, what'],
            ['Relative Pronoun', 'Connects a clause to a noun', 'who, which, that'],
            ['Indefinite Pronoun', 'Refers to non-specific people or things', 'someone, anyone, few'],
        ],
        'slides': [
            {
                'title': 'Pronouns Replace Nouns',
                'lines': [
                    'Riya is absent. She will join later.',
                    'The bags are heavy. They are near the door.',
                    'Pronouns make repeated ideas shorter and clearer.',
                ],
            },
            {
                'title': 'Choose the Right Form',
                'lines': [
                    'Subject form: She teaches English.',
                    'Object form: We called her yesterday.',
                    'Possessive form: That notebook is hers.',
                ],
            },
            {
                'title': 'Agreement Matters',
                'lines': [
                    'Each student must bring his or her ID.',
                    'The children enjoyed themselves at the park.',
                    'Match the pronoun with the noun in person and number.',
                ],
            },
        ],
        'video_title': 'Pronouns — Master the Basics',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/ZAdy-f7T_tU?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Pronouns replace nouns to avoid repetition in your sentences.',
            'Understand subject pronouns (I, he) vs. object pronouns (me, him).',
            'Use possessive pronouns like mine or hers to show ownership clearly.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main pronoun rules.',
        'audio_text': (
            'Pronouns are words we use in place of nouns. They help make our speech smoother and less repetitive. '
            'Subject pronouns like I or she perform the action, while object pronouns like me or her receive it. '
            'Always make sure your pronoun matches the person and number of the noun it is replacing.'
        ),
        'sections': [
            {
                'heading': 'Personal Pronouns',
                'lead': (
                    'Personal pronouns refer to people or things already known in the conversation. '
                    'They change their form depending on whether they work as subjects or objects.'
                ),
                'table_headers': ['Person', 'Subject Form', 'Object Form'],
                'table_rows': [
                    ['First person singular', 'I', 'me'],
                    ['Second person singular/plural', 'you', 'you'],
                    ['Third person singular masculine', 'he', 'him'],
                    ['Third person singular feminine', 'she', 'her'],
                    ['Third person singular neuter', 'it', 'it'],
                    ['First person plural', 'we', 'us'],
                    ['Third person plural', 'they', 'them'],
                ],
                'example_items': [
                    'I finished the homework before dinner.',
                    'The coach praised them after the match.',
                    'She called me when the class started.',
                ],
            },
            {
                'heading': 'Possessive and Reflexive Pronouns',
                'lead': (
                    'Possessive pronouns show ownership without repeating the noun. '
                    'Reflexive pronouns refer back to the same subject in a sentence.'
                ),
                'category_items': [
                    {'label': 'Possessive Pronouns', 'text': 'mine, yours, his, hers, ours, theirs'},
                    {'label': 'Reflexive Pronouns', 'text': 'myself, yourself, himself, herself, itself, ourselves, themselves'},
                    {'label': 'Emphatic Use', 'text': 'Use reflexive pronouns for emphasis: I wrote the report myself.'},
                ],
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'Do not use apostrophes in possessive pronouns. Write its, yours, ours, and theirs.'},
                    {'title': 'RULE 2', 'text': 'Use reflexive pronouns only when the subject and object are the same person or thing.'},
                    {'title': 'RULE 3', 'text': 'Avoid forms like myself went or himself is coming. Reflexive pronouns are not ordinary subjects.'},
                ],
                'example_items': [
                    'This victory is ours, not theirs.',
                    'He introduced himself to the new manager.',
                    'We decorated the hall ourselves.',
                ],
            },
            {
                'heading': 'Demonstrative, Interrogative, Relative and Indefinite Pronouns',
                'lead': 'These pronouns point, ask, connect, or refer to people and things in a general way.',
                'table_headers': ['Type', 'Purpose', 'Examples'],
                'table_rows': [
                    ['Demonstrative', 'Point to near or distant things', 'this, that, these, those'],
                    ['Interrogative', 'Ask questions', 'who, whom, whose, what, which'],
                    ['Relative', 'Join a clause to a noun', 'who, which, that, whose'],
                    ['Indefinite', 'Refer to non-specific people or things', 'someone, anybody, several, none'],
                ],
                'example_items': [
                    'This is the book that I was looking for.',
                    'Who left these keys on the table?',
                    'Someone has already answered the phone.',
                ],
            },
            {
                'heading': 'Pronoun Agreement and Common Errors',
                'lead': (
                    'A pronoun must match the noun it replaces in number and meaning. '
                    'Agreement mistakes are common when sentences contain collective or indefinite nouns.'
                ),
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'A singular noun needs a singular pronoun: The teacher forgot her notebook.'},
                    {'title': 'RULE 2', 'text': 'A plural noun needs a plural pronoun: The players washed their jerseys.'},
                    {'title': 'RULE 3', 'text': 'Be clear about the noun your pronoun refers to. If it is unclear, repeat the noun.'},
                ],
                'example_items': [
                    'Incorrect: Every student must bring their pen. Better: Every student must bring his or her pen.',
                    'Incorrect: When Rani met Sita, she smiled. Better: When Rani met Sita, Rani smiled.',
                    'Correct: The children packed their lunchboxes early.',
                ],
                'exercises': [
                    {'question': 'Q1. Replace the repeated noun: Riya said Riya would join after lunch.', 'answer': 'Riya said she would join after lunch.'},
                    {'question': 'Q2. Choose the correct pronoun: The boys lost (his / their) tickets.', 'answer': 'their'},
                    {'question': 'Q3. Fill in the blank: This bag is not mine. It is ________.', 'answer': 'yours'},
                ],
            },
        ],
    },
    'verb': {
        'slug': 'verb',
        'title': 'Verbs',
        'subtitle': 'Complete Guide with Types, Rules & Exercises',
        'badge': 'V',
        'accent_color': '#2f7a65',
        'definition': (
            'A verb is a word that shows an action, a state, or an occurrence. '
            'Every complete sentence needs a verb because verbs tell us what the subject does, is, or feels.'
        ),
        'role_items': [
            'Show actions such as run, write, and speak.',
            'Describe states such as is, seem, and belong.',
            'Help express tense, voice, mood, and condition.',
            'Connect the subject to important information in the sentence.',
        ],
        'summary_rows': [
            ['Action Verb', 'Shows physical or mental action', 'write, laugh, think'],
            ['Linking Verb', 'Connects the subject to more information', 'is, become, seem'],
            ['Helping Verb', 'Supports the main verb', 'is, have, do, will'],
            ['Modal Verb', 'Shows ability, advice, or possibility', 'can, should, may'],
            ['Transitive Verb', 'Takes a direct object', 'read a book'],
            ['Intransitive Verb', 'Does not take a direct object', 'sleep, arrive'],
            ['Phrasal Verb', 'Verb plus particle with a combined meaning', 'give up, look after'],
        ],
        'slides': [
            {
                'title': 'Verbs Drive Sentences',
                'lines': [
                    'Action: The child runs quickly.',
                    'State: The room feels warm.',
                    'Helping verbs build tense and meaning.',
                ],
            },
            {
                'title': 'Main Verb and Helping Verb',
                'lines': [
                    'She is reading a novel.',
                    'They have completed the project.',
                    'We will discuss the plan tomorrow.',
                ],
            },
            {
                'title': 'Objects and Complements',
                'lines': [
                    'Transitive: I opened the window.',
                    'Intransitive: The baby slept peacefully.',
                    'Linking: The soup smells delicious.',
                ],
            },
        ],
        'video_title': 'Verbs — Actions and States',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/dapJYDvqhwo?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Verbs are the engine of the sentence, showing actions or states.',
            'Action verbs show doing, while linking verbs show being.',
            'Helping verbs like is, have, and will add time and mood to your message.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main verb rules.',
        'audio_text': (
            'Verbs are words that show action or state. Every complete sentence must have a verb. '
            'Action verbs tell what the subject does, while linking verbs like is or seems connect the subject to more info. '
            'Helping verbs work with the main verb to create different tenses and show possibility.'
        ),
        'sections': [
            {
                'heading': 'Action, Linking and Helping Verbs',
                'lead': (
                    'These are the most important groups of verbs for beginners. '
                    'Knowing the difference helps you identify sentence meaning faster.'
                ),
                'table_headers': ['Verb Type', 'Function', 'Example'],
                'table_rows': [
                    ['Action Verb', 'Shows what the subject does', 'The students write neatly.'],
                    ['Linking Verb', 'Joins subject to a noun or adjective', 'The sky looks clear.'],
                    ['Helping Verb', 'Supports the main verb', 'She has finished her work.'],
                ],
                'example_items': [
                    'The cat jumped onto the sofa.',
                    'My uncle is a pilot.',
                    'They are preparing for the exam.',
                ],
            },
            {
                'heading': 'Main Verb, Helping Verb and Modals',
                'lead': 'Helping verbs and modal verbs add shades of meaning such as ability, necessity, possibility, and future time.',
                'category_items': [
                    {'label': 'Primary Helping Verbs', 'text': 'be, have, do'},
                    {'label': 'Modal Verbs', 'text': 'can, could, may, might, shall, should, will, would, must'},
                    {'label': 'Use', 'text': 'Use helping verbs before the main verb: She has written a letter.'},
                ],
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'Do not add -s to a verb after a modal. Write can speak, should go, will work.'},
                    {'title': 'RULE 2', 'text': 'Use do, does, and did to make negatives and questions in simple tenses.'},
                    {'title': 'RULE 3', 'text': 'Use have, has, or had with the past participle for perfect tenses.'},
                ],
                'example_items': [
                    'She can solve this problem alone.',
                    'Do they understand the instructions?',
                    'He has visited Chennai twice.',
                ],
            },
            {
                'heading': 'Transitive, Intransitive and Phrasal Verbs',
                'lead': (
                    'Some verbs need an object to complete their meaning, while others do not. '
                    'Phrasal verbs combine a verb with a particle to create a new meaning.'
                ),
                'two_col': [
                    {
                        'title': 'Transitive Verbs',
                        'items': [
                            'read a chapter',
                            'build a bridge',
                            'send a message',
                            'carry the box',
                        ],
                    },
                    {
                        'title': 'Intransitive Verbs',
                        'items': [
                            'sleep peacefully',
                            'arrive late',
                            'laugh loudly',
                            'fall suddenly',
                        ],
                    },
                ],
                'example_items': [
                    'Please turn off the lights before leaving.',
                    'The train arrived on time.',
                    'She looked after her little brother.',
                ],
            },
            {
                'heading': 'Subject-Verb Agreement and Common Errors',
                'lead': 'Verbs must agree with their subjects in number and person. This is one of the most important grammar rules in English.',
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'A singular subject takes a singular verb: The teacher explains the topic well.'},
                    {'title': 'RULE 2', 'text': 'A plural subject takes a plural verb: The teachers explain the topic well.'},
                    {'title': 'RULE 3', 'text': 'With he, she, and it in the simple present, add -s or -es: He runs fast.'},
                ],
                'example_items': [
                    'Incorrect: She go to school by bus. Correct: She goes to school by bus.',
                    'Incorrect: The players was tired. Correct: The players were tired.',
                    'Correct: Either Rani or her friends are planning the event.',
                ],
                'exercises': [
                    {'question': 'Q1. Identify the helping verb: They have finished the painting.', 'answer': 'have'},
                    {'question': 'Q2. Choose the correct verb: My brother (play / plays) football every evening.', 'answer': 'plays'},
                    {'question': 'Q3. Write one phrasal verb with look.', 'answer': 'look after / look for / look into'},
                ],
            },
        ],
    },
    'adjective': {
        'slug': 'adjective',
        'title': 'Adjectives',
        'subtitle': 'Complete Guide with Types, Rules & Exercises',
        'badge': 'Adj',
        'accent_color': '#b56a3b',
        'definition': (
            'An adjective is a word that describes or gives more information about a noun or pronoun. '
            'Adjectives tell us about quality, quantity, number, size, color, ownership, or identity.'
        ),
        'role_items': [
            'Describe how someone or something looks, feels, or behaves.',
            'Show number, quantity, and order.',
            'Point out or identify particular nouns.',
            'Compare two or more people, places, or things.',
        ],
        'summary_rows': [
            ['Descriptive Adjective', 'Tells quality or appearance', 'happy, blue, tall'],
            ['Quantitative Adjective', 'Shows amount', 'some, much, little'],
            ['Numeral Adjective', 'Shows number or order', 'three, first, many'],
            ['Demonstrative Adjective', 'Points out nouns', 'this book, those chairs'],
            ['Possessive Adjective', 'Shows belonging', 'my bag, their class'],
            ['Interrogative Adjective', 'Helps ask about nouns', 'which road, what color'],
            ['Proper Adjective', 'Comes from proper nouns', 'Indian food, French art'],
        ],
        'slides': [
            {
                'title': 'Adjectives Describe Nouns',
                'lines': [
                    'a bright lamp',
                    'three helpful students',
                    'her new notebook',
                ],
            },
            {
                'title': 'Placement Matters',
                'lines': [
                    'Before noun: a clever child',
                    'After linking verb: The child is clever.',
                    'Use commas with equal descriptive adjectives.',
                ],
            },
            {
                'title': 'Comparison',
                'lines': [
                    'tall, taller, tallest',
                    'more useful, most useful',
                    'good, better, best',
                ],
            },
        ],
        'video_title': 'Adjectives — Descriptive Words',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/fNriI8SbRgc?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Adjectives add color and detail to nouns and pronouns.',
            'They answer questions like: Which one? What kind? or How many?',
            'Use comparative forms (better) and superlative forms (best) for comparisons.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main adjective rules.',
        'audio_text': (
            'Adjectives describe nouns and pronouns. They give us details about size, color, number, and quality. '
            'Adjectives usually sit before the noun they describe or after a linking verb. '
            'When comparing things, remember to use comparative forms for two items and superlative forms for three or more.'
        ),
        'sections': [
            {
                'heading': 'Kinds of Adjectives',
                'lead': 'English uses many adjective groups. Each group answers a slightly different question about the noun.',
                'table_headers': ['Type', 'Question Answered', 'Examples'],
                'table_rows': [
                    ['Descriptive', 'What kind?', 'beautiful, noisy, brave'],
                    ['Quantitative', 'How much?', 'some, little, enough'],
                    ['Numeral', 'How many? Which number?', 'two, several, first'],
                    ['Demonstrative', 'Which one?', 'this, that, these, those'],
                    ['Possessive', 'Whose?', 'my, your, her, our'],
                ],
                'example_items': [
                    'She bought a red dress for the festival.',
                    'There is enough water for everyone.',
                    'Those students won the quiz competition.',
                ],
            },
            {
                'heading': 'Position of Adjectives',
                'lead': 'Adjectives usually come before nouns, but they can also follow linking verbs such as be, look, seem, feel, and become.',
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'Use adjectives before nouns: a clever answer, a clean classroom.'},
                    {'title': 'RULE 2', 'text': 'Use adjectives after linking verbs: The classroom is clean. The soup smells delicious.'},
                    {'title': 'RULE 3', 'text': 'When several adjectives describe one noun, use a natural order: a beautiful old wooden chair.'},
                ],
                'example_items': [
                    'The shy child hid behind her mother.',
                    'The child was shy during the performance.',
                    'They live in a small blue house near the river.',
                ],
            },
            {
                'heading': 'Degrees of Comparison',
                'lead': 'Adjectives can compare people or things. Use the positive degree for description, the comparative for two, and the superlative for three or more.',
                'table_headers': ['Positive', 'Comparative', 'Superlative'],
                'table_rows': [
                    ['tall', 'taller', 'tallest'],
                    ['easy', 'easier', 'easiest'],
                    ['beautiful', 'more beautiful', 'most beautiful'],
                    ['good', 'better', 'best'],
                    ['bad', 'worse', 'worst'],
                ],
                'example_items': [
                    'Ravi is taller than Kiran.',
                    'This is the most useful chapter in the book.',
                    'Today is better than yesterday.',
                ],
            },
            {
                'heading': 'Common Errors and Practice',
                'lead': 'Learners often confuse adjectives with adverbs or use the wrong comparison form. Checking the noun being described helps avoid mistakes.',
                'example_items': [
                    'Incorrect: She is more taller than me. Correct: She is taller than me.',
                    'Incorrect: He is a well boy. Correct: He is a healthy boy.',
                    'Correct: This is the best solution we found.',
                ],
                'exercises': [
                    {'question': 'Q1. Identify the adjective: The old bridge looks unsafe.', 'answer': 'old, unsafe'},
                    {'question': 'Q2. Fill in the blank with a possessive adjective: ________ brother is an engineer.', 'answer': 'My / Your / His / Her / Our / Their'},
                    {'question': 'Q3. Write the comparative and superlative of happy.', 'answer': 'happier, happiest'},
                ],
            },
        ],
    },
    'adverb': {
        'slug': 'adverb',
        'title': 'Adverbs',
        'subtitle': 'Complete Guide with Types, Rules & Exercises',
        'badge': 'Adv',
        'accent_color': '#a67c2e',
        'definition': (
            'An adverb is a word that modifies a verb, an adjective, another adverb, or an entire sentence. '
            'Adverbs tell us how, when, where, how often, or to what degree something happens.'
        ),
        'role_items': [
            'Describe the manner of an action.',
            'Show time, place, frequency, and degree.',
            'Modify adjectives and other adverbs.',
            'Add precision to statements, questions, and instructions.',
        ],
        'summary_rows': [
            ['Adverb of Manner', 'Shows how something happens', 'slowly, carefully'],
            ['Adverb of Time', 'Shows when something happens', 'today, soon, yesterday'],
            ['Adverb of Place', 'Shows where something happens', 'here, outside, everywhere'],
            ['Adverb of Frequency', 'Shows how often', 'always, often, rarely'],
            ['Adverb of Degree', 'Shows intensity or extent', 'very, quite, almost'],
            ['Sentence Adverb', 'Comments on the whole sentence', 'fortunately, honestly'],
        ],
        'slides': [
            {
                'title': 'Adverbs Add Detail',
                'lines': [
                    'She spoke clearly.',
                    'They arrived early.',
                    'The child is very curious.',
                ],
            },
            {
                'title': 'Different Adverb Questions',
                'lines': [
                    'How? carefully',
                    'When? tomorrow',
                    'How often? usually',
                ],
            },
            {
                'title': 'Position Changes Meaning',
                'lines': [
                    'He only borrowed the car.',
                    'He borrowed only the car.',
                    'Place adverbs carefully for clarity.',
                ],
            },
        ],
        'video_title': 'Adverbs — Modifying Actions',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/2O4ckpd_UjE?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Adverbs tell us how, when, where, or how often an action happens.',
            'Many adverbs are formed by adding -ly to an adjective.',
            'Adverbs can modify verbs, adjectives, or even other adverbs.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main adverb rules.',
        'audio_text': (
            'Adverbs add detail to verbs, adjectives, and other adverbs. They answer the questions: how, when, where, and how often. '
            'While many adverbs end in L-Y, others like often, fast, and hard do not. '
            'Be careful with where you place an adverb, as it can change the emphasis of your whole sentence.'
        ),
        'sections': [
            {
                'heading': 'Kinds of Adverbs',
                'lead': 'Adverbs can answer many different questions. Learning their jobs helps you place them correctly.',
                'table_headers': ['Type', 'Question Answered', 'Examples'],
                'table_rows': [
                    ['Manner', 'How?', 'carefully, loudly, gently'],
                    ['Time', 'When?', 'now, tomorrow, recently'],
                    ['Place', 'Where?', 'there, nearby, abroad'],
                    ['Frequency', 'How often?', 'often, never, sometimes'],
                    ['Degree', 'To what extent?', 'very, too, almost'],
                ],
                'example_items': [
                    'The nurse spoke softly to the patient.',
                    'We will travel tomorrow morning.',
                    'He almost missed the train.',
                ],
            },
            {
                'heading': 'Formation of Adverbs',
                'lead': 'Many adverbs are formed by adding -ly to adjectives, but some irregular forms must be memorized.',
                'category_items': [
                    {'label': 'Regular Formation', 'text': 'quick -> quickly, calm -> calmly, honest -> honestly'},
                    {'label': 'y to ily', 'text': 'happy -> happily, easy -> easily'},
                    {'label': 'Irregular Forms', 'text': 'good -> well, fast -> fast, hard -> hard, late -> late'},
                ],
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'Do not confuse adjectives and adverbs. She is a careful driver, but she drives carefully.'},
                    {'title': 'RULE 2', 'text': 'Some words can be both adjective and adverb: fast train, run fast.'},
                    {'title': 'RULE 3', 'text': 'Hardly does not mean hard. It means almost not.'},
                ],
                'example_items': [
                    'He sings well, not good.',
                    'The workers finished the road quickly.',
                    'The train moved fast through the station.',
                ],
            },
            {
                'heading': 'Position of Adverbs',
                'lead': 'Adverbs may appear at the beginning, middle, or end of a sentence, depending on the meaning and type.',
                'two_col': [
                    {
                        'title': 'Usually Mid Position',
                        'items': [
                            'She often visits her grandmother.',
                            'They have already eaten.',
                            'He never lies.',
                        ],
                    },
                    {
                        'title': 'Usually End Position',
                        'items': [
                            'The children played outside.',
                            'The teacher spoke clearly.',
                            'We met yesterday.',
                        ],
                    },
                ],
                'example_items': [
                    'Fortunately, the bus arrived on time.',
                    'I almost finished the assignment.',
                    'They will probably attend the workshop.',
                ],
            },
            {
                'heading': 'Common Errors and Practice',
                'lead': 'Adverb mistakes often happen when adjectives are used after action verbs or when words like only are placed carelessly.',
                'example_items': [
                    'Incorrect: She sang beautiful. Correct: She sang beautifully.',
                    'Incorrect: He drives reckless. Correct: He drives recklessly.',
                    'Correct: Only Riya answered the question.',
                ],
                'exercises': [
                    {'question': 'Q1. Identify the adverb: The baby slept peacefully.', 'answer': 'peacefully'},
                    {'question': 'Q2. Fill in the blank: He completed the work ________. (careful)', 'answer': 'carefully'},
                    {'question': 'Q3. Name the type of adverb in: We meet weekly.', 'answer': 'Adverb of frequency / time'},
                ],
            },
        ],
    },
    'conjunction': {
        'slug': 'conjunction',
        'title': 'Conjunctions',
        'subtitle': 'Complete Guide with Types, Rules & Exercises',
        'badge': 'Conj',
        'accent_color': '#5d698f',
        'definition': (
            'A conjunction is a word that joins words, phrases, clauses, or sentences. '
            'Conjunctions help ideas connect logically and smoothly in speech and writing.'
        ),
        'role_items': [
            'Join similar words or phrases.',
            'Connect independent and dependent clauses.',
            'Show addition, contrast, reason, result, and choice.',
            'Improve coherence in speaking and writing.',
        ],
        'summary_rows': [
            ['Coordinating Conjunction', 'Joins equal words or clauses', 'and, but, or, so'],
            ['Subordinating Conjunction', 'Introduces a dependent clause', 'because, although, if, when'],
            ['Correlative Conjunction', 'Works in pairs', 'either...or, neither...nor'],
            ['Conjunctive Adverb', 'Links ideas between clauses or sentences', 'however, therefore, moreover'],
        ],
        'slides': [
            {
                'title': 'Conjunctions Join Ideas',
                'lines': [
                    'Ria cooked and Aman cleaned.',
                    'We stayed inside because it rained.',
                    'Either call me or send a message.',
                ],
            },
            {
                'title': 'Different Logical Links',
                'lines': [
                    'Addition: and, moreover',
                    'Contrast: but, although, however',
                    'Reason/Result: because, so, therefore',
                ],
            },
            {
                'title': 'Clause Balance',
                'lines': [
                    'Use commas with some joined clauses.',
                    'Keep paired conjunctions balanced.',
                    'Choose the connector that matches meaning.',
                ],
            },
        ],
        'video_title': 'Conjunctions — Joining Ideas',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/4AyjKgz9tKg?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Conjunctions link words, phrases, and clauses together logically.',
            'Remember FANBOYS for coordinating conjunctions like And, But, and So.',
            'Use subordinating conjunctions (Because, If) to show relationships.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main conjunction rules.',
        'audio_text': (
            'Conjunctions are joining words. They connect parts of a sentence together. '
            'Coordinating conjunctions like and, but, and or join equal ideas. '
            'Subordinating conjunctions like because or although introduce a reason or contrast. '
            'Using them correctly makes your writing much more professional and easier to follow.'
        ),
        'sections': [
            {
                'heading': 'Coordinating Conjunctions',
                'lead': 'Coordinating conjunctions join words, phrases, or independent clauses of equal importance. The common set is remembered as FANBOYS.',
                'table_headers': ['Conjunction', 'Meaning', 'Example'],
                'table_rows': [
                    ['for', 'reason', 'She left early, for she was unwell.'],
                    ['and', 'addition', 'Arun sings and dances well.'],
                    ['nor', 'negative addition', 'He does not smoke, nor does he drink.'],
                    ['but', 'contrast', 'The road was narrow, but it was safe.'],
                    ['or', 'choice', 'Take a bus or hire a taxi.'],
                    ['yet', 'unexpected contrast', 'He is tired, yet he keeps working.'],
                    ['so', 'result', 'It was late, so we went home.'],
                ],
                'example_items': [
                    'The room was small but comfortable.',
                    'Ritu and Meera prepared the presentation.',
                    'Study now, or you may struggle later.',
                ],
            },
            {
                'heading': 'Subordinating Conjunctions',
                'lead': 'Subordinating conjunctions introduce dependent clauses and show relationships such as time, cause, purpose, condition, and contrast.',
                'category_items': [
                    {'label': 'Time', 'text': 'when, while, before, after, since, until'},
                    {'label': 'Reason', 'text': 'because, since, as'},
                    {'label': 'Condition', 'text': 'if, unless, provided that'},
                    {'label': 'Contrast', 'text': 'although, though, whereas'},
                ],
                'example_items': [
                    'We waited until the rain stopped.',
                    'Because she prepared well, she answered confidently.',
                    'Although he was tired, he finished the report.',
                ],
            },
            {
                'heading': 'Correlative Conjunctions and Conjunctive Adverbs',
                'lead': 'Correlative conjunctions come in pairs, while conjunctive adverbs link larger ideas and often need punctuation support.',
                'two_col': [
                    {
                        'title': 'Correlative Pairs',
                        'items': [
                            'either...or',
                            'neither...nor',
                            'both...and',
                            'not only...but also',
                        ],
                    },
                    {
                        'title': 'Conjunctive Adverbs',
                        'items': [
                            'however',
                            'therefore',
                            'moreover',
                            'nevertheless',
                        ],
                    },
                ],
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'Keep the same grammatical form after each correlative part: either tea or coffee, not either tea or to drink coffee.'},
                    {'title': 'RULE 2', 'text': 'Conjunctive adverbs often follow a semicolon and are followed by a comma: It rained; however, we continued.'},
                ],
                'example_items': [
                    'Both the principal and the teachers attended the event.',
                    'She was ill; therefore, she stayed home.',
                    'Not only the captain but also the team supported the plan.',
                ],
            },
            {
                'heading': 'Common Errors and Practice',
                'lead': 'Learners often overuse and or choose the wrong connector. Selecting a conjunction based on relationship makes writing clearer.',
                'example_items': [
                    'Incorrect: He was tired because he kept working. Better: He was tired, but he kept working.',
                    'Incorrect: Either you must study and leave. Better: Either you must study or leave.',
                    'Correct: Since the shop was closed, we returned home.',
                ],
                'exercises': [
                    {'question': 'Q1. Name the conjunction in: I stayed home because I was sick.', 'answer': 'because'},
                    {'question': 'Q2. Fill in the blank: ________ Riya nor Asha was late.', 'answer': 'Neither'},
                    {'question': 'Q3. Join the clauses with a suitable conjunction: It was hot. We went for a walk.', 'answer': 'It was hot, but we went for a walk. / Although it was hot, we went for a walk.'},
                ],
            },
        ],
    },
    'tenses': {
        'slug': 'tenses',
        'title': 'Tenses',
        'subtitle': 'Complete Guide with Forms, Uses & Exercises',
        'badge': 'T',
        'accent_color': '#3f6f8f',
        'definition': (
            'Tense shows the time of an action or state. English has present, past, and future time, and each of these can appear in simple, continuous, perfect, and perfect continuous forms.'
        ),
        'role_items': [
            'Show when an action happens.',
            'Explain whether an action is complete, continuing, repeated, or connected to another time.',
            'Help speakers describe habits, plans, experiences, and sequences clearly.',
            'Support accurate narration and explanation.',
        ],
        'summary_rows': [
            ['Simple Present', 'habit, truth, routine', 'She walks to school.'],
            ['Present Continuous', 'action happening now', 'She is walking now.'],
            ['Present Perfect', 'completed with present link', 'She has walked home.'],
            ['Simple Past', 'finished past action', 'She walked yesterday.'],
            ['Past Continuous', 'ongoing action in the past', 'She was walking at 5 pm.'],
            ['Past Perfect', 'action completed before another past action', 'She had walked before sunset.'],
            ['Simple Future', 'future plan or prediction', 'She will walk tomorrow.'],
            ['Future Continuous', 'action in progress in the future', 'She will be walking at noon.'],
        ],
        'slides': [
            {
                'title': 'Three Time Zones',
                'lines': [
                    'Present: I study English.',
                    'Past: I studied yesterday.',
                    'Future: I will study tonight.',
                ],
            },
            {
                'title': 'Four Main Forms',
                'lines': [
                    'Simple for facts and routines',
                    'Continuous for actions in progress',
                    'Perfect for completed actions with connection',
                ],
            },
            {
                'title': 'Clues in Context',
                'lines': [
                    'every day -> simple present',
                    'now -> present continuous',
                    'already, since, for -> perfect forms',
                ],
            },
        ],
        'video_title': 'English Tenses — The Masterclass',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/d0wV9EC3t14?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Tenses show the timing of actions: Past, Present, and Future.',
            'Each tense has four forms: Simple, Continuous, Perfect, and Perfect Continuous.',
            'Signal words like "yesterday" or "since" help you choose the right tense.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main tense rules.',
        'audio_text': (
            'English tenses tell us when an action happens and its current status. '
            'The three main time zones are past, present, and future. '
            'Each one has a simple form for facts, a continuous form for progress, and a perfect form for completed actions. '
            'Mastering tenses is the key to clear and accurate communication in English.'
        ),
        'sections': [
            {
                'heading': 'Present Tenses',
                'lead': 'Present forms talk about habits, current actions, completed actions connected to now, and duration up to now.',
                'table_headers': ['Tense', 'Form', 'Use', 'Example'],
                'table_rows': [
                    ['Simple Present', 'base / base+s', 'habit or fact', 'He reads daily.'],
                    ['Present Continuous', 'am/is/are + verb-ing', 'action happening now', 'He is reading now.'],
                    ['Present Perfect', 'has/have + past participle', 'completed with present result', 'He has read the chapter.'],
                    ['Present Perfect Continuous', 'has/have been + verb-ing', 'ongoing action with duration', 'He has been reading for two hours.'],
                ],
                'example_items': [
                    'The earth revolves around the sun.',
                    'They are preparing for the annual day.',
                    'She has lived here since 2020.',
                ],
            },
            {
                'heading': 'Past Tenses',
                'lead': 'Past forms describe finished actions, actions in progress in the past, earlier past actions, and duration before a point in the past.',
                'table_headers': ['Tense', 'Form', 'Use', 'Example'],
                'table_rows': [
                    ['Simple Past', 'verb-ed / irregular form', 'finished action', 'They visited Mysuru last year.'],
                    ['Past Continuous', 'was/were + verb-ing', 'past action in progress', 'They were visiting relatives at noon.'],
                    ['Past Perfect', 'had + past participle', 'earlier past action', 'They had visited before the festival began.'],
                    ['Past Perfect Continuous', 'had been + verb-ing', 'duration before a past time', 'They had been waiting for an hour.'],
                ],
                'example_items': [
                    'I finished the assignment yesterday.',
                    'She was cooking when the guests arrived.',
                    'The train had left before we reached the station.',
                ],
            },
            {
                'heading': 'Future Tenses',
                'lead': 'Future forms talk about plans, predictions, future actions in progress, completed future actions, and ongoing future duration.',
                'table_headers': ['Tense', 'Form', 'Use', 'Example'],
                'table_rows': [
                    ['Simple Future', 'will + base verb', 'future action or prediction', 'I will call you tomorrow.'],
                    ['Future Continuous', 'will be + verb-ing', 'future action in progress', 'I will be travelling at noon.'],
                    ['Future Perfect', 'will have + past participle', 'action completed before future time', 'I will have finished by 6 pm.'],
                    ['Future Perfect Continuous', 'will have been + verb-ing', 'future duration', 'I will have been working here for five years in June.'],
                ],
                'example_items': [
                    'We will start the workshop at ten.',
                    'They will be waiting outside the hall.',
                    'She will have completed the course by next month.',
                ],
            },
            {
                'heading': 'Time Markers and Common Errors',
                'lead': 'Tense choice becomes easier when you notice signal words and the order of events in the sentence.',
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'Use the simple present for routines and truths, not the present continuous: Water boils at 100 degrees Celsius.'},
                    {'title': 'RULE 2', 'text': 'Use the present perfect with since and for when the action started in the past and continues to the present.'},
                    {'title': 'RULE 3', 'text': 'Use the past perfect only when you need to show that one past action happened before another past action.'},
                ],
                'example_items': [
                    'Incorrect: I am knowing the answer. Correct: I know the answer.',
                    'Incorrect: She has gone yesterday. Correct: She went yesterday.',
                    'Correct: By the time I arrived, the film had started.',
                ],
                'exercises': [
                    {'question': 'Q1. Name the tense: They are playing in the garden.', 'answer': 'Present Continuous'},
                    {'question': 'Q2. Fill in the blank: She ________ the letter before dinner. (finish)', 'answer': 'finished / had finished depending on context'},
                    {'question': 'Q3. Write the future perfect form of complete.', 'answer': 'will have completed'},
                ],
            },
        ],
    },
    'sentence-structure': {
        'slug': 'sentence-structure',
        'title': 'Sentence Structure',
        'subtitle': 'Complete Guide with Patterns, Rules & Exercises',
        'badge': 'S',
        'accent_color': '#7a4f59',
        'definition': (
            'Sentence structure is the way words, phrases, and clauses are arranged to make clear meaning. '
            'A strong sentence usually needs a subject, a verb, and the correct order of ideas.'
        ),
        'role_items': [
            'Arrange words in a meaningful order.',
            'Help speakers and writers express clear complete thoughts.',
            'Show relationships between ideas through phrases and clauses.',
            'Prevent fragments, run-on sentences, and confusing order.',
        ],
        'summary_rows': [
            ['Subject', 'Tells who or what the sentence is about', 'The children'],
            ['Predicate', 'Tells what the subject does or is', 'played in the park'],
            ['Phrase', 'Group of words without a finite verb', 'in the morning'],
            ['Clause', 'Group of words with a subject and verb', 'because she worked hard'],
            ['Simple Sentence', 'One independent clause', 'The bell rang.'],
            ['Compound Sentence', 'Two independent clauses joined together', 'The bell rang, and the class ended.'],
            ['Complex Sentence', 'One independent clause plus one dependent clause', 'When the bell rang, the class ended.'],
        ],
        'slides': [
            {
                'title': 'Build the Core',
                'lines': [
                    'Subject + Verb = basic sentence',
                    'The birds sang.',
                    'Add details carefully around the core.',
                ],
            },
            {
                'title': 'Phrases and Clauses',
                'lines': [
                    'Phrase: under the table',
                    'Clause: because he was late',
                    'Clauses build sentence variety.',
                ],
            },
            {
                'title': 'Avoid Common Problems',
                'lines': [
                    'Fragment: Because it was raining.',
                    'Run-on: I came home I ate dinner.',
                    'Fix with a full main clause or punctuation.',
                ],
            },
        ],
        'video_title': 'Sentence Structure Basics',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/jul2urONzOQ?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'Every English sentence needs a subject and a verb to be complete.',
            'Learn the basic S-V-O pattern used in most common sentences.',
            'Avoid "run-on" sentences and fragments to keep your writing professional.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main sentence structure rules.',
        'audio_text': (
            'Sentence structure is the way we organize words to share a complete thought. '
            'A basic sentence needs a subject, which is who or what the sentence is about, and a predicate, which is the action. '
            'Understanding phrases and clauses helps you build more complex and interesting sentences.'
        ),
        'sections': [
            {
                'heading': 'Subject and Predicate',
                'lead': 'The subject names who or what the sentence is about. The predicate tells what the subject does, is, or experiences.',
                'table_headers': ['Sentence', 'Subject', 'Predicate'],
                'table_rows': [
                    ['The baby smiled.', 'The baby', 'smiled'],
                    ['Our team won the match.', 'Our team', 'won the match'],
                    ['The road is narrow.', 'The road', 'is narrow'],
                ],
                'example_items': [
                    'My sister enjoys painting landscapes.',
                    'The library opens at nine every morning.',
                    'Those flowers smell lovely.',
                ],
            },
            {
                'heading': 'Phrases and Clauses',
                'lead': 'A phrase does not contain a finite verb, while a clause has a subject and a verb. Clauses may be independent or dependent.',
                'two_col': [
                    {
                        'title': 'Common Phrases',
                        'items': [
                            'in the classroom',
                            'after lunch',
                            'with great care',
                            'on the shelf',
                        ],
                    },
                    {
                        'title': 'Common Clauses',
                        'items': [
                            'when the teacher arrived',
                            'because we were late',
                            'who lives nearby',
                            'if you need help',
                        ],
                    },
                ],
                'example_items': [
                    'The students waited in the corridor after lunch.',
                    'When the teacher arrived, the students became quiet.',
                    'I know the girl who won the prize.',
                ],
            },
            {
                'heading': 'Basic Sentence Patterns',
                'lead': 'English uses a few common sentence patterns. Recognizing them helps with writing and error correction.',
                'table_headers': ['Pattern', 'Meaning', 'Example'],
                'table_rows': [
                    ['S + V', 'Subject and verb only', 'Birds fly.'],
                    ['S + V + O', 'Subject, verb, object', 'She wrote a letter.'],
                    ['S + V + C', 'Subject, linking verb, complement', 'The sky became dark.'],
                    ['S + V + O + O', 'Indirect and direct object', 'He gave me a gift.'],
                    ['S + V + O + C', 'Object and complement', 'They elected Riya captain.'],
                ],
                'example_items': [
                    'The child laughed.',
                    'The teacher asked a question.',
                    'We painted the wall blue.',
                ],
            },
            {
                'heading': 'Fragments, Run-ons and Practice',
                'lead': 'Sentence problems happen when a thought is incomplete or when two complete thoughts are joined without proper punctuation or a connector.',
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'A fragment is incomplete: Because the bus was late. Add a main clause to complete the idea.'},
                    {'title': 'RULE 2', 'text': 'A run-on joins two full sentences without correct punctuation: I was hungry I cooked rice.'},
                    {'title': 'RULE 3', 'text': 'Use conjunctions, semicolons, or full stops to separate complete thoughts clearly.'},
                ],
                'example_items': [
                    'Fragment: After the meeting ended. Correct: After the meeting ended, we went home.',
                    'Run-on: The shop was closed we came back. Correct: The shop was closed, so we came back.',
                    'Correct: Because it was cold, we shut the windows.',
                ],
                'exercises': [
                    {'question': 'Q1. Identify the clause: We stayed indoors because it was raining.', 'answer': 'because it was raining'},
                    {'question': 'Q2. Name the sentence pattern: She opened the door.', 'answer': 'S + V + O'},
                    {'question': 'Q3. Correct the run-on: I reached home I called my mother.', 'answer': 'I reached home, and I called my mother. / I reached home. I called my mother.'},
                ],
            },
        ],
    },
    'types-of-sentences': {
        'slug': 'types-of-sentences',
        'title': 'Types of Sentences',
        'subtitle': 'Complete Guide with Forms, Uses & Exercises',
        'badge': 'TS',
        'accent_color': '#5a5f7a',
        'definition': 'Sentences can be grouped by purpose. The four main types are declarative, interrogative, imperative, and exclamatory.',
        'role_items': [
            'State facts and opinions clearly.',
            'Ask questions in direct and polite ways.',
            'Give commands, requests, and advice.',
            'Express strong feelings such as surprise, joy, or anger.',
        ],
        'summary_rows': [
            ['Declarative Sentence', 'Makes a statement', 'The train is late.'],
            ['Interrogative Sentence', 'Asks a question', 'Is the train late?'],
            ['Imperative Sentence', 'Gives a command or request', 'Please wait here.'],
            ['Exclamatory Sentence', 'Shows strong feeling', 'What a long delay this is!'],
        ],
        'slides': [
            {
                'title': 'Four Main Purposes',
                'lines': [
                    'Statement',
                    'Question',
                    'Command or request',
                    'Strong feeling',
                ],
            },
            {
                'title': 'End Punctuation',
                'lines': [
                    'Declarative -> period',
                    'Interrogative -> question mark',
                    'Exclamatory -> exclamation mark',
                ],
            },
            {
                'title': 'Tone and Intention',
                'lines': [
                    'Please close the window.',
                    'Could you close the window?',
                    'How cold it has become!',
                ],
            },
        ],
        'video_title': 'Types of Sentences — Explained',
        'video_embed_url': 'https://www.youtube-nocookie.com/embed/PLEpEMH0Tts?rel=0&modestbranding=1&playsinline=1',
        'video_points': [
            'There are four main types of sentences based on their purpose.',
            'Use Declarative for facts, Interrogative for questions, and Imperative for commands.',
            'Exclamatory sentences help you express strong feelings and emotion.',
        ],
        'audio_prompt': 'Play a short spoken recap of the main sentence type rules.',
        'audio_text': (
            'We choose different sentence types depending on why we are speaking. '
            'Declarative sentences are used most often to state facts. Interrogative sentences allow us to ask questions. '
            'Imperative sentences are for giving orders or making requests, and Exclamatory sentences let us show high emotion.'
        ),
        'sections': [
            {
                'heading': 'Declarative Sentences',
                'lead': 'A declarative sentence gives information, states an opinion, or reports a fact. It usually ends with a full stop.',
                'example_items': [
                    'The museum opens at ten o clock.',
                    'Our class enjoyed the science exhibition.',
                    'Honesty builds trust in a team.',
                ],
                'rule_boxes': [
                    {'title': 'Tip', 'text': 'Use declarative sentences when you want to explain, inform, or describe calmly and clearly.'},
                ],
            },
            {
                'heading': 'Interrogative Sentences',
                'lead': 'An interrogative sentence asks a question. It may begin with a helping verb or with a wh-word such as who, what, when, where, why, or how.',
                'table_headers': ['Question Type', 'Pattern', 'Example'],
                'table_rows': [
                    ['Yes/No Question', 'Helping verb + subject + main verb', 'Are you ready for the test?'],
                    ['Wh-question', 'Wh-word + helping verb + subject + main verb', 'Why are you smiling?'],
                    ['Choice Question', 'Alternative options in one question', 'Would you like tea or coffee?'],
                ],
                'example_items': [
                    'Did the train leave on time?',
                    'Where did you keep the files?',
                    'Can we begin the meeting now?',
                ],
            },
            {
                'heading': 'Imperative and Exclamatory Sentences',
                'lead': 'Imperative sentences give instructions, requests, suggestions, or warnings. Exclamatory sentences express strong emotion.',
                'two_col': [
                    {
                        'title': 'Imperative Examples',
                        'items': [
                            'Please sit down.',
                            'Turn off the fan.',
                            'Take care of your health.',
                            'Do not touch the wire.',
                        ],
                    },
                    {
                        'title': 'Exclamatory Examples',
                        'items': [
                            'What a beautiful rainbow this is!',
                            'How quickly the year passed!',
                            'That was an amazing performance!',
                            'What a relief!',
                        ],
                    },
                ],
                'rule_boxes': [
                    {'title': 'RULE 1', 'text': 'The subject you is usually understood in imperative sentences: Open the door. (You open the door.)'},
                    {'title': 'RULE 2', 'text': 'Exclamatory sentences often begin with what or how and end with an exclamation mark.'},
                ],
            },
            {
                'heading': 'Changing Sentence Types and Practice',
                'lead': 'One message can often be expressed in different sentence types depending on tone and purpose.',
                'example_items': [
                    'Declarative: You are coming with us.',
                    'Interrogative: Are you coming with us?',
                    'Imperative: Come with us.',
                    'Exclamatory: How wonderful it is that you are coming with us!',
                ],
                'exercises': [
                    {'question': 'Q1. Identify the type: Please close the notebook.', 'answer': 'Imperative'},
                    {'question': 'Q2. Change to an interrogative sentence: You finished the project.', 'answer': 'Did you finish the project? / Have you finished the project?'},
                    {'question': 'Q3. Write one exclamatory sentence about rain.', 'answer': 'Possible answer: What a heavy rain this is!'},
                ],
            },
        ],
    },
}


def _safe_file_response(file_path: Path) -> FileResponse:
    if not file_path.exists() or not file_path.is_file():
        raise Http404('Requested file was not found.')

    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path.open('rb'), content_type=content_type or 'application/octet-stream')


def _topic_cards():
    cards = []
    for topic in SUBJECT_TOPIC_CARDS:
        topic_copy = dict(topic)
        topic_copy['href'] = reverse('subject_topic', kwargs={'slug': topic['slug']})
        # FR-GRM-01 asks for an emoji alongside the summary and link. The topic
        # emoji already exists for the slide illustrations, so the index reuses
        # it rather than introducing a second set.
        topic_copy['emoji'] = TOPIC_EMOJI.get(topic['slug'], '📘')
        cards.append(topic_copy)
    return cards


def _topic_slide_urls(topic: TopicData) -> list[dict[str, str]]:
    deck = _deck_slide_urls(topic)
    if deck:
        return deck

    slides = []
    for index, slide in enumerate(topic['slides'], start=1):
        slides.append(
            {
                'src': reverse('subject_illustration', kwargs={'slug': topic['slug'], 'index': index}),
                'alt': slide['title'],
            }
        )
    return slides


def _deck_slide_urls(topic: TopicData) -> list[dict[str, str]]:
    """Real presentation slide images for a topic, in numeric order.

    Topics with a folder under ``static/subjectslides/<slug>/`` show those PNG
    decks as the Visual Guide, replacing the generated SVG illustrations. Files
    are ordered by the leading number in their name (01.png, 02.png, ...).
    """
    slug = topic['slug']
    deck_dir = SUBJECT_SLIDES_DIR / slug
    if not deck_dir.is_dir():
        return []

    def sort_key(path: Path):
        match = re.match(r'(\d+)', path.stem)
        return (int(match.group(1)) if match else 1_000_000, path.name.lower())

    image_paths = sorted(deck_dir.glob('*.png'), key=sort_key)
    return [
        {
            'src': reverse('subject_slide_image',
                           kwargs={'slug': slug, 'file_name': path.name}),
            'alt': f"{topic['title']} slide {index}",
        }
        for index, path in enumerate(image_paths, start=1)
    ]


def _topic_video_url(topic: TopicData) -> str:
    """URL for a topic's locally hosted lesson video, or '' if it has none.

    When ``static/subjectvideos/<slug>.mp4`` exists it is served through the
    range-aware ``subject_video`` view and used in place of the YouTube embed.
    Topics without a local file keep their ``video_embed_url`` fallback.
    """
    slug = topic['slug']
    if (SUBJECT_VIDEOS_DIR / f'{slug}.mp4').is_file():
        return reverse('subject_video', kwargs={'slug': slug})
    return ''


def _authored_slide_cards(topic: TopicData) -> list[dict[str, Any]]:
    """The authored slides paired with their own generated illustration.

    GRM-B02: `slides` below is replaced by image URLs for the carousel, so the
    authored title and lines never reached the template — the lesson existed only
    as pixels inside an SVG, unreachable to the page's language switcher, to
    find-in-page, to selection and to screen readers.

    GRM-B01: a topic's carousel can show a real PNG deck instead of the generated
    SVGs (see _deck_slide_urls), which would otherwise mean its authored slides
    were never shown at all. These cards are built from the authored slides for
    every topic, deck-backed ones included, so the written lesson always reaches
    the page.
    """
    cards = []
    for index, slide in enumerate(topic['slides'], start=1):
        cards.append({
            **slide,
            'src': reverse('subject_illustration',
                           kwargs={'slug': topic['slug'], 'index': index}),
            'alt': f"{topic['title']} — {slide['title']}",
        })
    return cards


def _topic_context(topic: TopicData) -> dict[str, Any]:
    return {
        **topic,
        # Carousel imagery: a real PNG deck when the topic has one, else generated SVG.
        'slides': _topic_slide_urls(topic),
        # The same lesson as real HTML, so it is readable without opening the viewer.
        'slide_cards': _authored_slide_cards(topic),
        'video_embed_url': topic.get('video_embed_url', DEFAULT_SUBJECT_VIDEO_EMBED_URL),
        # A locally hosted .mp4 when the topic has one; the template prefers it
        # over the YouTube embed above.
        'video_local_url': _topic_video_url(topic),
    }


# Fun, friendly emoji per grammar topic — used in the generated visual slides.
TOPIC_EMOJI = {
    'noun': '🏷️',
    'pronoun': '🔁',
    'verb': '⚡',
    'adjective': '🎨',
    'adverb': '🏃',
    'conjunction': '🔗',
    'tenses': '⏳',
    'sentence-structure': '🧱',
    'types-of-sentences': '💬',
}


def _build_illustration_svg(topic: TopicData, slide: SlideData, index: int) -> str:
    accent = topic['accent_color']
    accent_light = f'{accent}22'
    accent_soft = f'{accent}14'
    title = escape(topic['title'])
    slide_title = escape(slide['title'])
    emoji = TOPIC_EMOJI.get(topic.get('slug', ''), '📘')

    # Keep bullet lines tidy so they never overflow the card
    lines = []
    for line in slide['lines'][:4]:
        line = line.strip()
        if len(line) > 64:
            line = line[:63].rstrip() + '…'
        lines.append(escape(line))

    # Bullet baselines inside the 216–414 content panel.
    #
    # The slide heading sits on baseline 256, so a bullet must start no higher
    # than ~275 or its capitals run into the heading — at 270 the first line
    # collided with the title on every slide in every topic. Spacing then adapts
    # to the line count so four lines fit without losing the last point, which
    # is what "Four Main Purposes" used to do.
    line_y_positions = {
        1: [300],
        2: [292, 344],
        4: [288, 320, 352, 384],
    }.get(len(lines), [292, 336, 380])
    bullet_svg = []
    for y_pos, line in zip(line_y_positions, lines):
        bullet_svg.append(
            f'<circle cx="128" cy="{y_pos - 7}" r="7" fill="{accent}" />'
            f'<text x="152" y="{y_pos}" font-size="23" fill="#334155" '
            f'font-family="Manrope, Arial, sans-serif">{line}</text>'
        )
    bullet_markup = ''.join(bullet_svg)
    footer = escape(f'Slide {index} of {len(topic["slides"])}')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" role="img" aria-labelledby="title desc">
  <title id="title">{title} — {slide_title}</title>
  <desc id="desc">A fun visual guide for {title}.</desc>
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{accent_light}" />
      <stop offset="100%" stop-color="#ffffff" />
    </linearGradient>
    <linearGradient id="badge" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{accent}" />
      <stop offset="100%" stop-color="{accent}" stop-opacity="0.72" />
    </linearGradient>
    <filter id="softshadow" x="-10%" y="-10%" width="120%" height="135%">
      <feDropShadow dx="0" dy="12" stdDeviation="20" flood-color="{accent}" flood-opacity="0.20" />
    </filter>
  </defs>
  <rect width="960" height="540" rx="40" fill="url(#bg)" />
  <!-- playful decorative blobs -->
  <circle cx="882" cy="74" r="92" fill="{accent}" opacity="0.10" />
  <circle cx="70" cy="500" r="72" fill="{accent}" opacity="0.10" />
  <circle cx="915" cy="472" r="34" fill="{accent}" opacity="0.16" />
  <circle cx="812" cy="150" r="16" fill="{accent}" opacity="0.22" />
  <!-- main card -->
  <rect x="60" y="60" width="840" height="420" rx="30" fill="#ffffff" filter="url(#softshadow)" />
  <!-- emoji badge -->
  <rect x="96" y="94" width="98" height="98" rx="26" fill="url(#badge)" />
  <text x="145" y="163" text-anchor="middle" font-size="54">{emoji}</text>
  <text x="218" y="128" font-size="21" letter-spacing="3" font-weight="700" fill="{accent}" font-family="Manrope, Arial, sans-serif">GRAMMAR · LEARN &amp; PLAY</text>
  <text x="218" y="178" font-size="46" font-weight="800" fill="#0f172a" font-family="Manrope, Arial, sans-serif">{title}</text>
  <!-- content panel -->
  <rect x="96" y="216" width="768" height="198" rx="22" fill="{accent_soft}" />
  <text x="128" y="256" font-size="27" font-weight="800" fill="{accent}" font-family="Manrope, Arial, sans-serif">{slide_title}</text>
  {bullet_markup}
  <!-- footer pill -->
  <rect x="96" y="436" width="182" height="30" rx="15" fill="{accent}" opacity="0.16" />
  <text x="120" y="457" font-size="18" font-weight="700" fill="{accent}" font-family="Manrope, Arial, sans-serif">{footer}</text>
  <text x="822" y="460" font-size="30">{emoji}</text>
</svg>"""


@login_required
def subject_home(request):
    return render(
        request,
        'subject/home.html',
        {
            'topics': _topic_cards(),
        },
    )


@login_required
def subject_topic(request, slug: str):
    topic = SUBJECT_TOPICS.get(slug)
    if not topic:
        raise Http404('Topic not found.')

    return render(
        request,
        'subject/detail.html',
        {
            'topic': _topic_context(topic),
        },
    )


@login_required
def subject_slide_image(request, slug: str, file_name: str):
    if slug not in SUBJECT_TOPICS:
        raise Http404('Topic not found.')

    requested_name = Path(unquote(file_name))
    if requested_name.is_absolute() or '..' in requested_name.parts or len(requested_name.parts) != 1:
        raise Http404('Invalid image path.')

    return _safe_file_response(SUBJECT_SLIDES_DIR / slug / requested_name.name)


@login_required
def subject_video(request, slug: str):
    # The filename is derived from the validated slug, never from user input, so
    # there is no path to traverse.
    if slug not in SUBJECT_TOPICS:
        raise Http404('Topic not found.')

    video_path = SUBJECT_VIDEOS_DIR / f'{slug}.mp4'
    if not video_path.is_file():
        raise Http404('Video not found.')

    return _range_file_response(request, video_path, 'video/mp4')


def _range_file_response(request, path: Path, content_type: str):
    """Serve a file, honouring a single HTTP Range so the browser can seek.

    Django's FileResponse and static serve do not answer Range requests, so a
    video played through them can start but never seek. This returns 206 Partial
    Content for a single ``bytes=`` range and streams exactly that slice. It
    supports ``start-end``, open-ended ``start-`` and suffix ``-last_n`` forms;
    multi-part ranges fall back to the full 200 response.
    """
    file_size = path.stat().st_size
    # (\d*)-(\d*) covers start-end, start- and -suffix; reject the empty "-".
    match = re.match(r'bytes=(\d*)-(\d*)\s*$', request.headers.get('Range', ''))
    if not match or (not match.group(1) and not match.group(2)):
        response = FileResponse(path.open('rb'), content_type=content_type)
        response['Content-Length'] = str(file_size)
        response['Accept-Ranges'] = 'bytes'
        return response

    if not match.group(1):
        # Suffix range: the final N bytes of the file.
        suffix = int(match.group(2))
        start = max(0, file_size - suffix) if suffix else file_size
        end = file_size - 1
    else:
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else file_size - 1
        end = min(end, file_size - 1)
    if start > end or start >= file_size:
        response = HttpResponse(status=416)
        response['Content-Range'] = f'bytes */{file_size}'
        return response

    length = end - start + 1

    def stream():
        with path.open('rb') as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                chunk = handle.read(min(8192, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    response = StreamingHttpResponse(stream(), status=206, content_type=content_type)
    response['Content-Length'] = str(length)
    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response['Accept-Ranges'] = 'bytes'
    return response


@login_required
def subject_illustration(request, slug: str, index: int):
    topic = SUBJECT_TOPICS.get(slug)
    if not topic:
        raise Http404('Topic not found.')

    slides = cast(list[SlideData], topic['slides'])
    if index < 1 or index > len(slides):
        raise Http404('Illustration not found.')

    svg = _build_illustration_svg(topic, slides[index - 1], index)
    return HttpResponse(svg, content_type='image/svg+xml; charset=utf-8')
