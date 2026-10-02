"""
Management command: python manage.py populate_activities
Seeds all 20 Business English activities, sub-activities, and interactive
exercises, the three Interactive Workshop activities (Group Discussion,
JAM and Role Play), and — via setup_professional_modules — the four
professional AI modules (orders 21-24). 27 activities in total.

This command is idempotent and safe to re-run: it upserts content by natural
key instead of wiping the tables, so re-seeding never destroys learner progress
(UserProgress) or exercise scores (UserExerciseResult), and never duplicates or
re-orders activities.
"""
import copy

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from activities.models import Activity, SubActivity, Exercise, Question, BingoCard


ACTIVITIES_DATA = [
    {
        "order": 1, "title": "Elevator Pitch Workshop",
        "category": "speaking", "level": "Intermediate to Advanced",
        "duration": "60–90 min",
        "materials": "Timer, pitch template handouts, peer evaluation rubrics",
        "objective": "Students learn to deliver concise, persuasive presentations about a product, service, or business idea within 60 seconds.",
        "icon_class": "fas fa-microphone", "color_class": "primary",
        "subactivities": [
            {
                "order": 1, "title": "Pitch Structure Analysis",
                "description": "Present 3–4 example elevator pitches. Students identify key components: hook, problem, solution, value proposition, and call to action.",
                "instructions": "1. Review the 3 sample pitches provided below.\n2. For each pitch, identify: the Hook, Problem Statement, Solution, Value Proposition, and Call to Action.\n3. Note what makes each pitch effective or weak.\n4. Complete the pitch structure analysis worksheet.",
                "exercises": [
                    {
                        "title": "Identify Pitch Components (MCQ)",
                        "exercise_type": "mcq",
                        "instructions": "Choose the best answer for each question about elevator pitch structure.",
                        "questions": [
                            {"text": "Which component of an elevator pitch captures the listener's attention immediately?", "a": "Value Proposition", "b": "Call to Action", "c": "Hook", "d": "Solution", "correct": "c", "explanation": "The Hook is the opening statement designed to immediately engage the listener."},
                            {"text": "What is the main purpose of the 'Value Proposition' in an elevator pitch?", "a": "To ask for funding", "b": "To describe your background", "c": "To explain what makes your solution uniquely valuable", "d": "To list all product features", "correct": "c", "explanation": "The Value Proposition explains the unique benefit your solution offers compared to alternatives."},
                            {"text": "An effective elevator pitch should last approximately:", "a": "5 minutes", "b": "30 seconds to 2 minutes", "c": "10 minutes", "d": "15 seconds", "correct": "b", "explanation": "The ideal elevator pitch is between 30 seconds and 2 minutes — enough time to engage but brief enough to hold attention."},
                            {"text": "The 'Call to Action' in a pitch is best described as:", "a": "A description of the problem", "b": "A specific next step you want the listener to take", "c": "A list of your achievements", "d": "An introduction of your team", "correct": "b", "explanation": "A strong Call to Action directs the listener to a specific, actionable next step such as scheduling a meeting or visiting a website."},
                            {"text": "Which language style is most effective in an elevator pitch?", "a": "Technical jargon and complex vocabulary", "b": "Vague and general statements", "c": "Clear, concise, and persuasive language", "d": "Formal academic language", "correct": "c", "explanation": "Pitches should use clear, plain language that anyone can understand, combined with persuasive phrasing."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Draft and Refine",
                "description": "Students choose a product or business idea and write their pitch using the template. Pair up to exchange drafts.",
                "instructions": "1. Choose a product or business idea you are passionate about.\n2. Use the pitch template structure: Hook → Problem → Solution → Value Proposition → Call to Action.\n3. Write your 60-second pitch (approximately 120–150 words).\n4. Swap with a partner and give structured feedback.",
                "exercises": [
                    {
                        "title": "Fill in Your Pitch Template",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete each part of the pitch template with the correct business English term.",
                        "questions": [
                            {"text": "The opening statement that immediately grabs the listener's attention is called the ___.", "correct": "hook", "explanation": "Hook – the first thing you say to engage your audience"},
                            {"text": "The section where you explain what challenge your customer faces is the ___ statement.", "correct": "problem", "explanation": "Problem statement – defines the pain point your product/service solves"},
                            {"text": "The part of the pitch that explains how your product/service addresses the problem is the ___.", "correct": "solution", "explanation": "Solution – your product/service and how it works"},
                            {"text": "What makes your solution uniquely better than alternatives is your ___ ___.", "correct": "value proposition", "explanation": "Value Proposition – your competitive advantage"},
                            {"text": "The final part where you ask for a specific next step is the ___ to ___.", "correct": "call to action", "explanation": "Call to Action – what you want the listener to do next"},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Timed Delivery and Feedback",
                "description": "Each student delivers their 60-second pitch to a small group. Audience members score using a rubric.",
                "instructions": "1. Prepare your final 60-second pitch.\n2. Use the timer below to practice your delivery.\n3. Focus on: clarity, persuasiveness, vocabulary, and confident body language.\n4. After delivery, review the peer scoring rubric.",
                "exercises": [
                    {
                        "title": "60-Second Pitch Timer",
                        "exercise_type": "timer",
                        "instructions": "Use this timer to practice your elevator pitch delivery. Press Start and deliver your pitch before the timer runs out.",
                        "questions": [
                            {"text": "Practice Delivery: Deliver your full elevator pitch in 60 seconds or less.", "explanation": "Speak clearly and hit all 5 components: Hook, Problem, Solution, Value Proposition, Call to Action."},
                            {"text": "Cold Opening: Try starting your pitch with only the hook — no introduction of your name.", "explanation": "Starting with a strong hook before your name creates immediate engagement."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 2, "title": "Business Negotiation Simulation",
        "category": "negotiation", "level": "Intermediate to Advanced",
        "duration": "90–120 min",
        "materials": "Role cards, negotiation scenario briefs, agreement templates",
        "objective": "Students practice negotiation strategies, persuasive language, conditional structures, and compromise techniques in realistic business contexts.",
        "icon_class": "fas fa-handshake", "color_class": "success",
        "subactivities": [
            {
                "order": 1, "title": "Negotiation Language Workshop",
                "description": "Teach key phrases for proposing, counter-offering, and compromising.",
                "instructions": "1. Study the negotiation phrase bank below.\n2. Categorise each phrase by function: Proposing, Counter-offering, Compromising, or Rejecting.\n3. Practise using each phrase in a short sentence.",
                "exercises": [
                    {
                        "title": "Match Negotiation Phrases to Functions",
                        "exercise_type": "matching",
                        "instructions": "Match each negotiation phrase on the left with its correct function on the right. Click a left item, then click its matching right item.",
                        "questions": [
                            {"left": "'We'd be willing to… if you could…'", "right": "Conditional Offer / Proposing", "correct": "Conditional Offer / Proposing"},
                            {"left": "'I understand your position, however…'", "right": "Polite Rebuttal / Counter-offering", "correct": "Polite Rebuttal / Counter-offering"},
                            {"left": "'Could we perhaps meet halfway on…?'", "right": "Seeking Compromise", "correct": "Seeking Compromise"},
                            {"left": "'That's outside our current budget, but…'", "right": "Softening a Rejection", "correct": "Softening a Rejection"},
                            {"left": "'Let me take that back to my team.'", "right": "Buying Time / Stalling", "correct": "Buying Time / Stalling"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Role-Based Preparation",
                "description": "Distribute confidential role cards. Each party prepares their strategy, identifying best alternatives and key concessions.",
                "instructions": "1. Read your role card carefully.\n2. Identify your BATNA (Best Alternative To a Negotiated Agreement).\n3. List your 3 key priorities and 2 acceptable concessions.\n4. Prepare your opening offer and 2 fallback positions.",
                "exercises": [
                    {
                        "title": "Negotiation Strategy Quiz",
                        "exercise_type": "mcq",
                        "instructions": "Test your understanding of negotiation strategy before entering your role-play.",
                        "questions": [
                            {"text": "What does BATNA stand for?", "a": "Best Alternative To a Negotiated Agreement", "b": "Business Approach To Negotiating Agreements", "c": "Basic Advancement Through Negotiation Actions", "d": "Better Alternative Towards Agreed Norms", "correct": "a", "explanation": "BATNA is your best alternative if negotiations fail — knowing it gives you negotiating power."},
                            {"text": "Which of the following is an example of 'anchoring' in negotiation?", "a": "Agreeing immediately to the first offer", "b": "Making the first offer to set the reference point", "c": "Waiting for the other party to speak first", "d": "Avoiding any specific numbers", "correct": "b", "explanation": "Anchoring means making the first offer to establish the starting point of the negotiation in your favour."},
                            {"text": "Hedging language in negotiation is used to:", "a": "Make strong, direct demands", "b": "Soften statements and reduce confrontation", "c": "End a negotiation quickly", "d": "Agree to all terms", "correct": "b", "explanation": "Hedging language ('perhaps', 'possibly', 'we might consider') reduces confrontation and keeps discussions open."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Live Negotiation and Debrief",
                "description": "Pairs or groups conduct their negotiation while the instructor circulates. Afterward, report outcomes and discuss strategies.",
                "instructions": "1. Conduct a 15–20 minute negotiation with your partner.\n2. Use the phrase bank from Sub-Activity 1.\n3. Record your final agreement or breakdown.\n4. Complete the debrief reflection below.",
                "exercises": [
                    {
                        "title": "Negotiation Outcome Reflection",
                        "exercise_type": "writing",
                        "instructions": "Write a structured reflection on your negotiation experience covering all prompts.",
                        "questions": [
                            {"text": "Describe the outcome of your negotiation. Did you reach an agreement? What were the key terms? What concessions did you make?", "explanation": "Aim for 80–120 words. Use past tense and business vocabulary."},
                            {"text": "What negotiation phrases from the phrase bank did you use effectively? Give 2 specific examples with context.", "explanation": "Reference actual phrases: 'We'd be willing to… if you could…' etc."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 3, "title": "Professional Email Communication",
        "category": "writing", "level": "Pre-Intermediate to Advanced",
        "duration": "60–90 min",
        "materials": "Sample email bank, tone comparison chart, email writing checklist",
        "objective": "Students master tone, structure, and conventions of professional emails for enquiries, complaints, follow-ups, and apologies.",
        "icon_class": "fas fa-envelope", "color_class": "info",
        "subactivities": [
            {
                "order": 1, "title": "Email Anatomy and Tone Analysis",
                "description": "Present pairs of emails (formal vs. informal) on the same topic. Students identify differences and build a tone reference chart.",
                "instructions": "1. Compare the formal and informal email pairs.\n2. Identify differences in: greeting, closing, sentence structure, vocabulary, and tone.\n3. Complete the formal equivalent chart below.",
                "exercises": [
                    {
                        "title": "Formal vs Informal Vocabulary Match",
                        "exercise_type": "matching",
                        "instructions": "Match each informal expression on the left with its formal business email equivalent on the right.",
                        "questions": [
                            {"left": "I want to know about...", "right": "I would appreciate information regarding...", "correct": "I would appreciate information regarding..."},
                            {"left": "Sorry for the mess-up", "right": "I sincerely apologise for the inconvenience caused", "correct": "I sincerely apologise for the inconvenience caused"},
                            {"left": "Can you send me...?", "right": "Could you please forward...", "correct": "Could you please forward..."},
                            {"left": "Thanks a lot", "right": "Thank you for your assistance", "correct": "Thank you for your assistance"},
                            {"left": "We need this ASAP", "right": "We would appreciate your prompt response", "correct": "We would appreciate your prompt response"},
                            {"left": "Get back to me", "right": "I look forward to your reply", "correct": "I look forward to your reply"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Scenario-Based Email Drafting",
                "description": "Each student drafts an email for a specific scenario, then swaps with a partner for tone and structure review.",
                "instructions": "1. Select one scenario from the list.\n2. Draft a professional email using correct format: Subject, Greeting, Body (opening, main point, action), Closing, Sign-off.\n3. Use the checklist to self-review before submission.",
                "exercises": [
                    {
                        "title": "Email Structure Fill-in-the-Blank",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete each blank with the correct business email component or phrase.",
                        "questions": [
                            {"text": "The first line of a professional email before the recipient's name is called the ___.", "correct": "salutation", "explanation": "Also called the greeting — e.g., 'Dear Mr Smith,'"},
                            {"text": "A professional email always ends with a ___ close such as 'Yours sincerely' or 'Kind regards'.", "correct": "complimentary", "explanation": "The complimentary close signals the end of the email body."},
                            {"text": "The ___ line tells the recipient what the email is about before they open it.", "correct": "subject", "explanation": "A clear subject line improves open rates and professionalism."},
                            {"text": "When writing to someone you do not know, the correct salutation is 'Dear ___ Madam'.", "correct": "Sir or", "explanation": "'Dear Sir or Madam' is used when the recipient's name is unknown."},
                            {"text": "In a complaint email, you should acknowledge the issue, ___ for the inconvenience, and offer a solution.", "correct": "apologise", "explanation": "Apologising early in a complaint response shows empathy and professionalism."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Reply Chain Challenge",
                "description": "Students respond to an increasingly complex email thread, maintaining consistency and professionalism.",
                "instructions": "1. Read the email chain scenario carefully.\n2. Write 3 professional replies: initial request, response to a misunderstanding, and a resolution email.\n3. Maintain consistent tone throughout the chain.",
                "exercises": [
                    {
                        "title": "Email Chain Writing Practice",
                        "exercise_type": "writing",
                        "instructions": "Write professional email replies for each stage of the scenario email chain below.",
                        "questions": [
                            {"text": "SCENARIO — Initial Email: A client has written asking you to expedite delivery of their order (Order #4521) originally due in 3 weeks. Write your reply explaining what you can do.", "explanation": "Use: Dear [Name], Thank you for your email... We understand... We are pleased to / Unfortunately we are unable to... Please do not hesitate to contact..."},
                            {"text": "FOLLOW-UP: The client has replied saying there was a misunderstanding — they needed only 50 units expedited, not the full 200. Write a clarifying and apologetic reply.", "explanation": "Acknowledge the misunderstanding, apologise briefly, confirm the revised arrangement clearly."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 4, "title": "Case Study Analysis and Presentation",
        "category": "analysis", "level": "Upper-Intermediate to Advanced",
        "duration": "120–150 min",
        "materials": "Printed case studies, SWOT/PESTLE templates, presentation guidelines",
        "objective": "Students analyze real-world business problems, develop solutions using analytical frameworks, and present recommendations using professional language.",
        "icon_class": "fas fa-search-dollar", "color_class": "warning",
        "subactivities": [
            {
                "order": 1, "title": "Framework Introduction",
                "description": "Teach SWOT analysis and business frameworks. Students practice with guided worksheets.",
                "instructions": "1. Study the SWOT and PESTLE frameworks.\n2. Match each factor below to its correct category in the framework.\n3. Apply the framework to the sample company case.",
                "exercises": [
                    {
                        "title": "SWOT vs PESTLE Classification",
                        "exercise_type": "mcq",
                        "instructions": "Classify each factor into the correct framework category.",
                        "questions": [
                            {"text": "A new government regulation increases compliance costs for a company. In PESTLE, this is classified as:", "a": "Political", "b": "Economic", "c": "Social", "d": "Legal", "correct": "d", "explanation": "Legal factors in PESTLE include regulations, legislation, and compliance requirements."},
                            {"text": "A company has a patent on a unique technology competitor cannot replicate. In SWOT, this is:", "a": "Weakness", "b": "Opportunity", "c": "Strength", "d": "Threat", "correct": "c", "explanation": "A unique patent is an internal strength that provides competitive advantage."},
                            {"text": "Rising consumer preference for eco-friendly products is best classified as:", "a": "Strength", "b": "Opportunity", "c": "Weakness", "d": "Threat", "correct": "b", "explanation": "External trends that a company can capitalise on are SWOT Opportunities."},
                            {"text": "A competitor launching a superior product at a lower price is a SWOT:", "a": "Strength", "b": "Weakness", "c": "Opportunity", "d": "Threat", "correct": "d", "explanation": "External factors that could harm the business are classified as Threats."},
                            {"text": "Increasing disposable income among target customers is a PESTLE ___ factor:", "a": "Political", "b": "Economic", "c": "Technological", "d": "Environmental", "correct": "b", "explanation": "Economic factors include income levels, inflation, and purchasing power."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Group Analysis Session",
                "description": "Groups analyze a case study and draft recommendations using the chosen framework.",
                "instructions": "1. Read the assigned case study.\n2. Apply SWOT or PESTLE to identify key factors.\n3. Draft 3–5 actionable recommendations with supporting reasoning.\n4. Assign each recommendation to a team member for presentation.",
                "exercises": [
                    {
                        "title": "Recommendation Writing",
                        "exercise_type": "writing",
                        "instructions": "Write structured business recommendations based on your case study analysis.",
                        "questions": [
                            {"text": "Write 3 actionable recommendations for your case study company. Each recommendation must include: What to do, Why (linked to SWOT/PESTLE findings), and Expected outcome.", "explanation": "Use language such as: 'We recommend that the company...', 'This would enable...', 'Based on our analysis...', 'The anticipated result is...'"},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Boardroom-Style Presentation",
                "description": "Groups present their analysis and recommendations. Other groups play board members asking challenging questions.",
                "instructions": "1. Prepare a 10-minute structured presentation.\n2. Cover: Executive Summary, Key Findings, Recommendations, Q&A.\n3. Practise handling challenging questions using the language guide below.",
                "exercises": [
                    {
                        "title": "Handling Q&A Language",
                        "exercise_type": "matching",
                        "instructions": "Match each challenging question type with the best response strategy.",
                        "questions": [
                            {"left": "You don't have enough data to support this.", "right": "Acknowledge + Clarify: 'That's a valid point. Our analysis is based on... and we acknowledge that further data would...'", "correct": "Acknowledge + Clarify: 'That's a valid point. Our analysis is based on... and we acknowledge that further data would...'"},
                            {"left": "What is your risk mitigation plan?", "right": "Structure: 'We've identified three key risks... For each, our mitigation strategy is...'", "correct": "Structure: 'We've identified three key risks... For each, our mitigation strategy is...'"},
                            {"left": "Have you considered alternative solutions?", "right": "Comparison: 'Yes, we evaluated X and Y alternatives. We selected this approach because...'", "correct": "Comparison: 'Yes, we evaluated X and Y alternatives. We selected this approach because...'"},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 5, "title": "Meeting Management Workshop",
        "category": "negotiation", "level": "Intermediate to Advanced",
        "duration": "90–120 min",
        "materials": "Sample agendas, meeting role cards, minutes template, phrase bank",
        "objective": "Students learn to chair, participate in, and minute professional meetings using appropriate language for agenda-setting, turn-taking, summarising, and action-point assignment.",
        "icon_class": "fas fa-users", "color_class": "purple",
        "subactivities": [
            {
                "order": 1, "title": "Meeting Language Toolkit",
                "description": "Introduce functional language for chairing, contributing, disagreeing diplomatically, and summarising.",
                "instructions": "1. Study the meeting language phrase bank.\n2. Categorise each phrase by its function.\n3. Practise using each phrase in context.",
                "exercises": [
                    {
                        "title": "Categorise Meeting Phrases",
                        "exercise_type": "mcq",
                        "instructions": "Select the correct function for each meeting phrase.",
                        "questions": [
                            {"text": "'Let's move on to item three on the agenda.' — This phrase is used for:", "a": "Disagreeing politely", "b": "Chairing/Managing agenda flow", "c": "Summarising decisions", "d": "Asking for opinions", "correct": "b", "explanation": "Agenda management phrases help the chairperson keep the meeting on track."},
                            {"text": "'I see your point, however, I believe we should consider...' — This phrase is used for:", "a": "Agreeing strongly", "b": "Closing the meeting", "c": "Disagreeing diplomatically", "d": "Assigning action items", "correct": "c", "explanation": "Diplomatic disagreement acknowledges the speaker's view while introducing a different perspective."},
                            {"text": "'So what we've agreed is...' — This phrase is used for:", "a": "Opening the meeting", "b": "Turn-taking", "c": "Summarising decisions", "d": "Asking for clarification", "correct": "c", "explanation": "Summarising phrases confirm what was agreed and help with accurate minute-taking."},
                            {"text": "'Could I just add something here?' — This phrase is used for:", "a": "Closing the discussion", "b": "Taking a turn politely", "c": "Assigning action points", "d": "Chairing the meeting", "correct": "b", "explanation": "Turn-taking phrases allow participants to enter the conversation without interrupting."},
                            {"text": "'Action point: John will send the revised budget by Friday.' — This phrase is used for:", "a": "Summarising", "b": "Disagreeing", "c": "Assigning action items", "d": "Opening remarks", "correct": "c", "explanation": "Action point language assigns specific responsibilities with clear deadlines."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Agenda-Driven Role Play",
                "description": "Assign roles: chairperson, minute-taker, and participants with specific viewpoints. Run a realistic meeting for 20–25 minutes.",
                "instructions": "1. Read your role card carefully.\n2. The chairperson will open the meeting and manage the agenda.\n3. Use the phrase bank from Sub-Activity 1 throughout.\n4. Minute-taker records decisions and action items.",
                "exercises": [
                    {
                        "title": "Meeting Agenda Fill-in-the-Blank",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete this professional meeting agenda template with the correct terms.",
                        "questions": [
                            {"text": "The list of topics to be discussed in a meeting is called the ___.", "correct": "agenda", "explanation": "Agendas are shared in advance so participants can prepare."},
                            {"text": "The person responsible for running and facilitating a meeting is the ___ or meeting chair.", "correct": "chairperson", "explanation": "Also called the 'chair' — responsible for keeping the meeting on track."},
                            {"text": "The written record of what was discussed and agreed in a meeting is called the ___.", "correct": "minutes", "explanation": "Minutes are an official record distributed to all attendees after the meeting."},
                            {"text": "A specific task assigned to a person with a deadline during a meeting is called an ___ point.", "correct": "action", "explanation": "Action points ensure accountability and follow-through after meetings."},
                            {"text": "'A.O.B.' at the end of an agenda stands for Any ___ Business.", "correct": "Other", "explanation": "AOB gives participants a chance to raise points not on the official agenda."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Minutes Review and Feedback",
                "description": "The minute-taker shares notes. The class compares versions and identifies what should and should not be included.",
                "instructions": "1. Review the sample meeting minutes provided.\n2. Identify errors: too much detail, missing action items, unclear deadlines.\n3. Revise the minutes to professional standard.",
                "exercises": [
                    {
                        "title": "Meeting Minutes Correction",
                        "exercise_type": "writing",
                        "instructions": "Rewrite the poorly formatted meeting minutes excerpt into professional format.",
                        "questions": [
                            {"text": "POOR MINUTES EXCERPT: 'John said he thought the marketing budget was maybe too high and Sarah disagreed and said it was fine actually but then Mark said we should think about it more and everyone talked for a while.' — Rewrite this as a proper meeting minute entry.", "explanation": "Good minutes use: objective language, clear decisions, action items with owners and deadlines. Avoid personal opinions and vague language."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 6, "title": "Job Interview Mastery",
        "category": "speaking", "level": "Pre-Intermediate to Advanced",
        "duration": "90–120 min",
        "materials": "Job descriptions, interview question bank, STAR method guide, evaluation forms",
        "objective": "Students practice answering and asking interview questions confidently using the STAR method, appropriate register, and professional body language.",
        "icon_class": "fas fa-briefcase", "color_class": "danger",
        "subactivities": [
            {
                "order": 1, "title": "STAR Method Training",
                "description": "Explain the STAR technique (Situation, Task, Action, Result) with examples. Students draft STAR responses.",
                "instructions": "1. Study the STAR method: Situation → Task → Action → Result.\n2. Read the sample STAR response provided.\n3. Draft your own STAR response for a common interview question.\n4. Partner review for structure and language.",
                "exercises": [
                    {
                        "title": "STAR Method MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Test your understanding of the STAR interview technique.",
                        "questions": [
                            {"text": "In the STAR method, 'S' stands for:", "a": "Strategy", "b": "Situation", "c": "Success", "d": "Skills", "correct": "b", "explanation": "Situation — describe the context and background of the example you are about to share."},
                            {"text": "The 'Action' part of STAR should focus on:", "a": "What your team collectively did", "b": "The problem that arose", "c": "What YOU specifically did to address the situation", "d": "The final outcome", "correct": "c", "explanation": "Interviewers want to know YOUR specific contribution — use 'I' not 'we'."},
                            {"text": "The 'Result' in a STAR response is most effective when it:", "a": "Describes what went wrong", "b": "Is vague to avoid over-promising", "c": "Includes quantifiable outcomes where possible", "d": "Focuses on what the company did", "correct": "c", "explanation": "Quantified results (e.g., 'increased sales by 30%') make your answer more credible and memorable."},
                            {"text": "Which opening best introduces the 'Situation' in a STAR response?", "a": "'I believe I am a great candidate because...'", "b": "'In my previous role at X, I was responsible for...'", "c": "'My greatest strength is...'", "d": "'I would handle this by...'", "correct": "b", "explanation": "Begin with a specific context from a real experience to ground your answer."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Mock Interview Rounds",
                "description": "Pair students as interviewer and candidate using real job descriptions. Roles swap after 15 minutes.",
                "instructions": "1. As the interviewer: ask 4 behavioural questions from the question bank.\n2. As the candidate: use STAR method for each answer.\n3. After each round, provide structured feedback using the rubric.",
                "exercises": [
                    {
                        "title": "Interview Phrase Fill-in-the-Blank",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete these professional interview phrases with the correct word.",
                        "questions": [
                            {"text": "To introduce a STAR example: 'In my ___ role at [Company], I faced a situation where...'", "correct": "previous", "explanation": "'Previous role' or 'former position' introduces your experience professionally."},
                            {"text": "To show impact: 'As a ___, we reduced customer complaints by 40% within three months.'", "correct": "result", "explanation": "'As a result' introduces the quantified outcome of your actions."},
                            {"text": "To show teamwork: 'I ___ with cross-functional teams to ensure the project was delivered on time.'", "correct": "collaborated", "explanation": "'Collaborated' is a strong professional verb showing teamwork skills."},
                            {"text": "To ask a good question at the end: 'Could you describe the ___ development opportunities available in this role?'", "correct": "professional", "explanation": "Asking about professional development shows ambition and long-term commitment."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Panel Interview Simulation",
                "description": "Form panels of 3–4 interviewers. One candidate faces the panel for 10 minutes. Class discusses performance.",
                "instructions": "1. Each panellist focuses on a different area: technical skills, teamwork, leadership, or culture fit.\n2. The candidate must address each panellist's question clearly.\n3. Complete the post-interview reflection form.",
                "exercises": [
                    {
                        "title": "Interview Reflection Writing",
                        "exercise_type": "writing",
                        "instructions": "Write a structured post-interview reflection after your panel interview experience.",
                        "questions": [
                            {"text": "Reflect on your panel interview performance. Address: (1) Which question was hardest and why? (2) How well did you apply the STAR method? (3) What would you improve in a real interview?", "explanation": "Use professional reflection language: 'I found it challenging when...', 'In hindsight, I would...', 'My strongest response was...'"},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 7, "title": "Business Report Writing",
        "category": "writing", "level": "Upper-Intermediate to Advanced",
        "duration": "90–150 min",
        "materials": "Sample reports, data sets, report structure template, style guide",
        "objective": "Students produce structured, data-driven business reports with executive summaries, findings, analysis, and recommendations using formal academic-business register.",
        "icon_class": "fas fa-file-alt", "color_class": "teal",
        "subactivities": [
            {
                "order": 1, "title": "Report Structure Deconstruction",
                "description": "Students identify and label report sections and analyse writing style and tone.",
                "instructions": "1. Read the sample business report provided.\n2. Identify and label each section: Executive Summary, Introduction, Methodology, Findings, Recommendations, Conclusion.\n3. Note the purpose and tone of each section.",
                "exercises": [
                    {
                        "title": "Match Report Sections to Purposes",
                        "exercise_type": "matching",
                        "instructions": "Match each report section on the left with its correct purpose on the right.",
                        "questions": [
                            {"left": "Executive Summary", "right": "A brief overview of the entire report including key findings and recommendations", "correct": "A brief overview of the entire report including key findings and recommendations"},
                            {"left": "Methodology", "right": "Explains how data was collected and the research approach used", "correct": "Explains how data was collected and the research approach used"},
                            {"left": "Findings", "right": "Presents the data, results, and factual information discovered", "correct": "Presents the data, results, and factual information discovered"},
                            {"left": "Recommendations", "right": "Proposes specific actions based on the analysis of findings", "correct": "Proposes specific actions based on the analysis of findings"},
                            {"left": "Conclusion", "right": "Summarises key points and reinforces the main message without new information", "correct": "Summarises key points and reinforces the main message without new information"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Data Interpretation and Writing",
                "description": "Students write a findings section, practising language for describing trends and drawing conclusions.",
                "instructions": "1. Study the dataset provided (sales figures and market trends).\n2. Use the trend description phrase bank to write a findings paragraph.\n3. Include comparisons, trend descriptions, and one conclusion.",
                "exercises": [
                    {
                        "title": "Trend Language Fill-in-the-Blank",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete each sentence with the correct trend-description phrase.",
                        "questions": [
                            {"text": "Sales revenue ___ sharply in Q3, reaching a record high of $2.4 million.", "correct": "rose", "explanation": "Use 'rose', 'increased', or 'grew' for upward trends."},
                            {"text": "Customer complaints ___ steadily over the six-month period, indicating improving service quality.", "correct": "declined", "explanation": "'Declined', 'fell', or 'decreased' describe downward trends."},
                            {"text": "Revenue ___ between $1.2M and $1.5M throughout the year, with no clear trend.", "correct": "fluctuated", "explanation": "'Fluctuated' describes irregular movement without a clear direction."},
                            {"text": "Market share ___ at 34% for three consecutive quarters before beginning to rise.", "correct": "remained stable", "explanation": "'Remained stable', 'held steady', or 'plateaued' describe no change."},
                            {"text": "Profits ___ at $3.1M in June before declining in the following quarter.", "correct": "peaked", "explanation": "'Peaked' describes reaching the highest point before declining."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Executive Summary Challenge",
                "description": "Students write a 150-word executive summary. Peers evaluate for clarity and conciseness.",
                "instructions": "1. Based on the full report data provided, write a 150-word executive summary.\n2. Include: purpose of report, 2 key findings, and 1 main recommendation.\n3. Use formal, concise language — no jargon.",
                "exercises": [
                    {
                        "title": "Write an Executive Summary",
                        "exercise_type": "writing",
                        "instructions": "Write a professional 150-word executive summary for the quarterly performance report described below.",
                        "questions": [
                            {"text": "REPORT CONTEXT: A mid-size retail company saw Q3 revenue rise 18% to $4.2M, driven by online sales (+34%). However, in-store sales fell 12%. Operating costs increased 8% due to staffing. Three stores underperformed against targets. Recommendation needed on store strategy vs. digital investment.\n\nWrite the Executive Summary (150 words max).", "explanation": "Structure: 1 sentence purpose → 2–3 key findings → 1 recommendation. Use past tense for findings, present/future for recommendations."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 8, "title": "Cross-Cultural Communication",
        "category": "communication", "level": "Intermediate to Advanced",
        "duration": "60–90 min",
        "materials": "Cultural dimension profiles, scenario cards, reflection worksheets",
        "objective": "Students develop awareness of cultural differences in business communication and practice adapting their style for diverse professional contexts.",
        "icon_class": "fas fa-globe", "color_class": "orange",
        "subactivities": [
            {
                "order": 1, "title": "Cultural Dimensions Exploration",
                "description": "Introduce Hofstede's cultural dimensions. Students identify where their own culture sits on each dimension.",
                "instructions": "1. Study Hofstede's 5 cultural dimensions: Power Distance, Individualism, Uncertainty Avoidance, Long-Term Orientation, Indulgence.\n2. For each dimension, identify which end of the spectrum best describes your culture.\n3. Compare with a partner from a different cultural background.",
                "exercises": [
                    {
                        "title": "Cultural Dimensions MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Test your knowledge of Hofstede's cultural dimensions and their impact on business communication.",
                        "questions": [
                            {"text": "In a high 'Power Distance' culture, employees are most likely to:", "a": "Frequently challenge their manager's decisions", "b": "Expect flat organisational structures", "c": "Accept hierarchical authority without question", "d": "Make decisions independently without approval", "correct": "c", "explanation": "High power distance cultures accept inequality and respect authority figures without challenging them."},
                            {"text": "A 'high-context' communication culture (e.g., Japan, China) relies heavily on:", "a": "Explicit, direct written contracts", "b": "Implicit messages, relationships, and non-verbal cues", "c": "Detailed verbal instructions", "d": "Avoiding face-to-face communication", "correct": "b", "explanation": "High-context cultures communicate meaning through context, relationships, and non-verbal signals."},
                            {"text": "Which behaviour is typical of a high 'Individualism' culture?", "a": "Group harmony is prioritised over personal goals", "b": "Personal achievement and autonomy are highly valued", "c": "Employees always consult the group before deciding", "d": "Loyalty to the company is lifelong", "correct": "b", "explanation": "Individualistic cultures (e.g., USA, UK) prioritise personal achievement and self-reliance."},
                            {"text": "When doing business with a high 'Uncertainty Avoidance' culture, you should:", "a": "Present vague, flexible proposals", "b": "Avoid providing documentation", "c": "Provide detailed plans, contracts, and clear structures", "d": "Rely on verbal agreements only", "correct": "c", "explanation": "High uncertainty avoidance cultures feel more comfortable with detailed structures and formal agreements."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Cross-Cultural Scenario Role Play",
                "description": "Pairs role-play cross-cultural business scenarios first incorrectly (ignoring cultural differences) then correctly (adapting style).",
                "instructions": "1. Read your cross-cultural scenario card.\n2. First role-play WITHOUT cultural adaptation — notice what goes wrong.\n3. Re-role-play WITH cultural awareness — observe the difference.\n4. Reflect on the changes you made.",
                "exercises": [
                    {
                        "title": "Adapting Communication Style Quiz",
                        "exercise_type": "mcq",
                        "instructions": "Choose the most culturally appropriate communication approach for each scenario.",
                        "questions": [
                            {"text": "You are emailing a Japanese business partner to decline their proposal. The most appropriate approach is:", "a": "'We don't want to do this deal. Please find another partner.'", "b": "'We have carefully considered your proposal and, while we appreciate the opportunity, we feel this may not be the right fit at this time. We hope to explore future collaborations.'", "c": "'No thanks.'", "d": "'This proposal does not meet our criteria.'", "correct": "b", "explanation": "Japanese business culture is high-context and values indirect, face-saving communication. A softened, respectful refusal maintains the relationship."},
                            {"text": "In a meeting with German colleagues, they push back strongly on your proposal. You should:", "a": "End the meeting — they are being rude", "b": "Apologise immediately and withdraw your proposal", "c": "Provide detailed data and logical arguments to support your position", "d": "Change the subject to avoid conflict", "correct": "c", "explanation": "German business culture values directness and evidence-based debate — strong pushback is normal and means they are engaged."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Communication Style Adaptation",
                "description": "Students rewrite a direct email for a high-context audience and vice versa.",
                "instructions": "1. Read the direct (low-context) email provided.\n2. Rewrite it for a high-context cultural audience.\n3. Then take the indirect email and rewrite it for a direct cultural context.\n4. Note the changes in tone, structure, and phrasing.",
                "exercises": [
                    {
                        "title": "Rewrite for Cultural Context",
                        "exercise_type": "writing",
                        "instructions": "Rewrite the email below for the specified cultural audience.",
                        "questions": [
                            {"text": "ORIGINAL (direct/low-context style): 'Hi Team, The project deadline is Friday. You are behind schedule. Please submit all sections by EOD Thursday or there will be consequences. — Manager'\n\nRewrite this for a high-context (indirect) cultural audience while conveying the same urgency.", "explanation": "High-context rewrite should: open warmly, acknowledge effort, express the urgency indirectly but clearly, avoid threats, end positively. E.g., 'Dear Team, I hope this finds you well...'"},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 9, "title": "Product Launch Planning",
        "category": "speaking", "level": "Intermediate to Advanced",
        "duration": "120–180 min",
        "materials": "Marketing plan template, budget spreadsheet, presentation tools",
        "objective": "Students collaborate to plan a comprehensive product launch including market research, branding, pricing, marketing strategy, and a final investor pitch.",
        "icon_class": "fas fa-rocket", "color_class": "rose",
        "subactivities": [
            {
                "order": 1, "title": "Market Research and Positioning",
                "description": "Teams research competitors, identify target demographics, and determine a USP.",
                "instructions": "1. Select a product category for your launch.\n2. Identify 3 key competitors and their positioning.\n3. Define your target demographic (age, profession, income, needs).\n4. Write your Unique Selling Proposition (USP) in one sentence.",
                "exercises": [
                    {
                        "title": "Market Research Vocabulary",
                        "exercise_type": "mcq",
                        "instructions": "Choose the correct definition for each market research term.",
                        "questions": [
                            {"text": "A 'Unique Selling Proposition (USP)' is:", "a": "The lowest price in the market", "b": "The one feature or benefit that makes your product different from and better than competitors", "c": "The number of products sold in the first week", "d": "Your company's mission statement", "correct": "b", "explanation": "A USP clearly communicates what makes your product uniquely valuable to your target customer."},
                            {"text": "A 'target demographic' refers to:", "a": "The total size of the market", "b": "The specific group of people most likely to buy your product", "c": "Your company's marketing team", "d": "The price point of your product", "correct": "b", "explanation": "Demographics include age, gender, income, location, and lifestyle of your ideal customer."},
                            {"text": "In a product launch, 'market positioning' means:", "a": "Where your product is displayed in a store", "b": "How you want customers to perceive your product relative to competitors", "c": "Your distribution channel strategy", "d": "The physical location of your launch event", "correct": "b", "explanation": "Positioning defines the space you occupy in the customer's mind — premium, affordable, innovative, etc."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Marketing Mix Development",
                "description": "Teams develop their marketing mix (4Ps) and create a budget allocation table.",
                "instructions": "1. Define your product's 4Ps: Product, Price, Place, Promotion.\n2. Create a budget allocation table with percentages for each marketing channel.\n3. Write justifications for each spending decision using business language.",
                "exercises": [
                    {
                        "title": "The 4Ps of Marketing — Matching",
                        "exercise_type": "matching",
                        "instructions": "Match each marketing mix element with its correct description.",
                        "questions": [
                            {"left": "Product", "right": "Features, quality, design, branding, and packaging of what you sell", "correct": "Features, quality, design, branding, and packaging of what you sell"},
                            {"left": "Price", "right": "Pricing strategy, discounts, payment terms, and value perception", "correct": "Pricing strategy, discounts, payment terms, and value perception"},
                            {"left": "Place", "right": "Distribution channels — where and how customers can buy the product", "correct": "Distribution channels — where and how customers can buy the product"},
                            {"left": "Promotion", "right": "Advertising, social media, PR, and all customer communication strategies", "correct": "Advertising, social media, PR, and all customer communication strategies"},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Investor Pitch Presentation",
                "description": "Teams deliver a 10–15 minute investor pitch. Other teams act as venture capitalists asking tough questions.",
                "instructions": "1. Prepare a 10–15 minute investor pitch covering: Market Opportunity, Product/USP, Go-to-Market Strategy, Financial Projections, Ask.\n2. Anticipate 5 tough questions from the VCs.\n3. Use the timer below to practise your pitch.",
                "exercises": [
                    {
                        "title": "Investor Pitch Practice Timer",
                        "exercise_type": "timer",
                        "instructions": "Use the 60-second timer to practise each key section of your investor pitch.",
                        "questions": [
                            {"text": "Market Opportunity: Describe the problem and the market size in 60 seconds.", "explanation": "Include: the problem, who has it, and the market size (TAM/SAM/SOM)."},
                            {"text": "Your Solution & USP: Explain what your product does and why it's better than existing solutions.", "explanation": "Be specific about your differentiator. Avoid vague claims like 'it's unique'."},
                            {"text": "The Ask: Explain how much funding you need, what you will use it for, and what investors get in return.", "explanation": "Be specific: '£500,000 for 15% equity, used to fund product development and first-year marketing.'"},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 10, "title": "Business Telephone and Video Calls",
        "category": "communication", "level": "Pre-Intermediate to Intermediate",
        "duration": "60–90 min",
        "materials": "Call scripts, role cards, phone/video call phrase bank, recording devices",
        "objective": "Students practice telephone and video call etiquette including opening, clarifying, summarising, and closing calls professionally.",
        "icon_class": "fas fa-phone", "color_class": "emerald",
        "subactivities": [
            {
                "order": 1, "title": "Call Opening and Closing Drills",
                "description": "Teach standard phrases for answering, transferring, holding, and closing calls politely.",
                "instructions": "1. Study the professional call phrase bank.\n2. Match each phrase to the correct stage of a business call.\n3. Practise in rapid-fire pairs, rotating every 2 minutes.",
                "exercises": [
                    {
                        "title": "Match Call Phrases to Stages",
                        "exercise_type": "matching",
                        "instructions": "Match each telephone phrase to the correct stage of a professional business call.",
                        "questions": [
                            {"left": "'Good morning, Acme Ltd, Sarah speaking. How may I help you?'", "right": "Call Opening / Answering", "correct": "Call Opening / Answering"},
                            {"left": "'Could I take a message and have her call you back?'", "right": "Taking a Message", "correct": "Taking a Message"},
                            {"left": "'Could you hold the line, please? I'll transfer you now.'", "right": "Transferring a Call", "correct": "Transferring a Call"},
                            {"left": "'Just to confirm, you need delivery on the 15th to your Manchester office?'", "right": "Clarifying / Confirming Details", "correct": "Clarifying / Confirming Details"},
                            {"left": "'Thank you for calling. Have a great day. Goodbye.'", "right": "Call Closing", "correct": "Call Closing"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Information Gap Calls",
                "description": "Pairs sit back-to-back to simulate real calls, exchanging information to complete their records.",
                "instructions": "1. Partner A has a shipping schedule; Partner B has a customer order list.\n2. Conduct a professional phone call to exchange the missing information.\n3. Record the call if possible and review for clarity and professionalism.",
                "exercises": [
                    {
                        "title": "Professional Call Vocabulary",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete these professional telephone phrases with the correct word.",
                        "questions": [
                            {"text": "To ask someone to wait: 'Could you ___ the line for a moment, please?'", "correct": "hold", "explanation": "'Hold the line' is the standard professional phrase for putting someone on brief hold."},
                            {"text": "To check understanding: 'I'm sorry, could you ___ that, please?'", "correct": "repeat", "explanation": "'Could you repeat that?' politely asks for clarification without sounding rude."},
                            {"text": "To confirm a time: 'So that's a meeting on Tuesday at 3pm. Does that ___ for you?'", "correct": "work", "explanation": "'Does that work for you?' is a polite way to confirm a scheduled time."},
                            {"text": "When transferring: 'I'll ___ you through to our sales department.'", "correct": "put", "explanation": "'Put you through' is the standard phrase for transferring a call."},
                            {"text": "To end professionally: 'Thank you for calling. I'll ___ up on this by end of day.'", "correct": "follow", "explanation": "'Follow up' commits you to a next action and leaves a positive impression."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Problem-Solving Call Simulation",
                "description": "Students navigate obstacle calls (unavailable person, misunderstanding, rescheduling) and record for self-review.",
                "instructions": "1. Use the scenario cards to conduct a problem-solving phone call.\n2. Navigate obstacles: wrong department, misunderstood information, complaint resolution.\n3. Complete the self-assessment checklist after your call.",
                "exercises": [
                    {
                        "title": "Call Handling MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Choose the most professional response for each telephone scenario.",
                        "questions": [
                            {"text": "A caller asks for your manager who is unavailable. The most professional response is:", "a": "'She's not here. Call back later.'", "b": "'I'm afraid she's unavailable at the moment. May I take a message or transfer you to her voicemail?'", "c": "'Hold on.'", "d": "'She doesn't want to talk to anyone.'", "correct": "b", "explanation": "A professional response acknowledges the situation, offers alternatives (message or voicemail), and maintains courtesy."},
                            {"text": "A caller speaks too quickly and you didn't catch their name. You should:", "a": "Guess the name and hope for the best", "b": "Say nothing and continue the call", "c": "'I'm sorry, I didn't quite catch your name. Could you spell that for me, please?'", "d": "'Speak slower!'", "correct": "c", "explanation": "Politely asking for clarification is professional and ensures accuracy — never guess or stay silent."},
                            {"text": "When ending a call, the most professional closing is:", "a": "'OK bye'", "b": "'Thank you for calling. I'll follow up on that by end of day. Goodbye.'", "c": "'We'll see'", "d": "'Yeah, sure. Later.'", "correct": "b", "explanation": "A strong close confirms next steps, expresses appreciation, and maintains professionalism to the very end."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 11, "title": "Financial Literacy and Reporting",
        "category": "analysis", "level": "Upper-Intermediate to Advanced",
        "duration": "90–120 min",
        "materials": "Sample financial statements, glossary handout, chart-reading exercises",
        "objective": "Students learn to read, discuss, and present financial information using accurate terminology for profit and loss, balance sheets, and financial trends.",
        "icon_class": "fas fa-chart-line", "color_class": "indigo",
        "subactivities": [
            {
                "order": 1, "title": "Financial Vocabulary Building",
                "description": "Introduce key financial terms using matching exercises and gap-fill activities with real financial news excerpts.",
                "instructions": "1. Study the financial glossary terms.\n2. Complete the matching exercise connecting terms to definitions.\n3. Create 2 example sentences for 5 key terms.",
                "exercises": [
                    {
                        "title": "Financial Terms Matching",
                        "exercise_type": "matching",
                        "instructions": "Match each financial term to its correct definition.",
                        "questions": [
                            {"left": "Revenue", "right": "Total income generated from sales before any costs are deducted", "correct": "Total income generated from sales before any costs are deducted"},
                            {"left": "EBITDA", "right": "Earnings Before Interest, Taxes, Depreciation and Amortisation", "correct": "Earnings Before Interest, Taxes, Depreciation and Amortisation"},
                            {"left": "Gross Margin", "right": "Revenue minus cost of goods sold, expressed as a percentage", "correct": "Revenue minus cost of goods sold, expressed as a percentage"},
                            {"left": "Liabilities", "right": "Financial obligations and debts owed by the company", "correct": "Financial obligations and debts owed by the company"},
                            {"left": "Cash Flow", "right": "The movement of money into and out of the business over a period", "correct": "The movement of money into and out of the business over a period"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Financial Statement Analysis",
                "description": "Students analyse simplified financial statements and describe company financial health using hedging language.",
                "instructions": "1. Review the simplified Profit & Loss statement and Balance Sheet provided.\n2. Calculate: Gross Profit Margin, Net Profit Margin, and Debt-to-Equity Ratio.\n3. Write a 100-word paragraph describing the company's financial health using appropriate hedging language.",
                "exercises": [
                    {
                        "title": "Financial Analysis MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Answer these questions based on financial statement analysis skills.",
                        "questions": [
                            {"text": "If a company has Revenue of £500K and Cost of Goods Sold of £300K, the Gross Profit is:", "a": "£800K", "b": "£300K", "c": "£200K", "d": "£150K", "correct": "c", "explanation": "Gross Profit = Revenue − Cost of Goods Sold = £500K − £300K = £200K"},
                            {"text": "A Debt-to-Equity ratio of 0.4 suggests:", "a": "The company is heavily leveraged and at high financial risk", "b": "The company has more equity than debt — relatively conservative financing", "c": "The company has no assets", "d": "Revenue equals expenses", "correct": "b", "explanation": "A low D/E ratio (<1) means the company is primarily equity-financed, which is generally considered lower risk."},
                            {"text": "Which financial statement shows a company's assets, liabilities, and equity at a specific point in time?", "a": "Profit and Loss Statement", "b": "Cash Flow Statement", "c": "Balance Sheet", "d": "Income Statement", "correct": "c", "explanation": "The Balance Sheet (Statement of Financial Position) provides a snapshot of what a company owns and owes at a specific date."},
                            {"text": "Hedging language in financial reporting (e.g., 'appears to', 'suggests that') is used to:", "a": "Exaggerate results for investors", "b": "Acknowledge uncertainty and avoid overstating conclusions", "c": "Confuse readers", "d": "Avoid providing financial data", "correct": "b", "explanation": "Hedging language in financial analysis reflects analytical caution — the data supports a conclusion but doesn't guarantee it."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Quarterly Earnings Presentation",
                "description": "Each group prepares a 5-minute earnings report for a fictional company. Shareholders ask questions.",
                "instructions": "1. Using the fictional company data provided, prepare a 5-minute earnings presentation.\n2. Include: Revenue, Profit, Key Variances, Forward Guidance.\n3. Practise with the timer, then present to your group as shareholders.",
                "exercises": [
                    {
                        "title": "Earnings Presentation Writing",
                        "exercise_type": "writing",
                        "instructions": "Write a structured 5-minute earnings script for the fictional company data below.",
                        "questions": [
                            {"text": "COMPANY DATA — TechPro Ltd Q3: Revenue £8.2M (+12% YoY), Gross Margin 64% (+2pp), Operating Costs £4.1M (+18%), Net Profit £1.1M (-8% YoY). New product launch delayed to Q4. Board recommends dividend of £0.15/share.\n\nWrite the earnings presentation script (200–250 words). Address: performance highlights, challenges, and forward guidance.", "explanation": "Structure: Opening → Revenue/Growth → Margins → Challenges → Outlook → Dividend/Q&A invitation. Use financial vocabulary and hedging language."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 12, "title": "Business Correspondence: Letters and Memos",
        "category": "writing", "level": "Pre-Intermediate to Intermediate",
        "duration": "60–90 min",
        "materials": "Letter and memo templates, sample correspondence, formatting guide",
        "objective": "Students master the conventions of formal business letters and internal memos, including layout, tone, and purpose-specific structures.",
        "icon_class": "fas fa-mail-bulk", "color_class": "pink",
        "subactivities": [
            {
                "order": 1, "title": "Format and Convention Study",
                "description": "Compare business letter format with memo format. Students identify differences in tone, audience, and purpose.",
                "instructions": "1. Study both the business letter and memo format examples.\n2. Identify 5 key structural differences between them.\n3. Complete the format comparison table.",
                "exercises": [
                    {
                        "title": "Letter vs Memo: Key Differences MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Choose the correct answer about business letter and memo conventions.",
                        "questions": [
                            {"text": "A business letter is typically sent to:", "a": "Internal staff only", "b": "External parties such as clients, suppliers, or government agencies", "c": "Only senior management", "d": "Social media audiences", "correct": "b", "explanation": "Business letters are formal external documents sent outside the organisation."},
                            {"text": "A memo (memorandum) is primarily used for:", "a": "External client communication", "b": "Social media announcements", "c": "Internal communication within an organisation", "d": "Legal contracts", "correct": "c", "explanation": "Memos communicate internal information — policies, announcements, updates — within the organisation."},
                            {"text": "Which salutation is correct for a formal business letter when you know the recipient's name?", "a": "'Hey John,'", "b": "'Hi there,'", "c": "'Dear Mr Johnson,'", "d": "'To Whom,'", "correct": "c", "explanation": "'Dear [Title] [Surname],' is the standard formal salutation when you know the recipient's name."},
                            {"text": "A business memo typically begins with which header block?", "a": "Date, Address, Salutation", "b": "TO, FROM, DATE, SUBJECT", "c": "Dear Sir/Madam, Body, Yours faithfully", "d": "Title, Abstract, Body", "correct": "b", "explanation": "Memos use a structured header: TO, FROM, DATE, SUBJECT — no salutation or complimentary close needed."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Purpose-Driven Drafting",
                "description": "Students write a formal letter to a client and a memo to staff, emphasising appropriate register shifts.",
                "instructions": "1. Write a formal letter confirming an order to a client.\n2. Write a memo announcing a policy change to your team.\n3. Notice the register shift: external (formal) vs. internal (professional but less formal).",
                "exercises": [
                    {
                        "title": "Fill in the Business Letter",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete this formal business letter with the correct words or phrases.",
                        "questions": [
                            {"text": "When writing to someone whose name you don't know, use: 'Dear ___ or Madam'", "correct": "Sir", "explanation": "'Dear Sir or Madam' is used for unknown recipients in formal letters."},
                            {"text": "When you know the recipient's name, close with: '___ sincerely'", "correct": "Yours", "explanation": "'Yours sincerely' is paired with a named salutation ('Dear Mr/Ms [Name]')."},
                            {"text": "When you write 'Dear Sir or Madam', the complementary close is 'Yours ___'", "correct": "faithfully", "explanation": "'Yours faithfully' is used when the recipient is unknown ('Dear Sir or Madam')."},
                            {"text": "To refer to a previous communication: 'Further to our telephone ___ of 5 May...'", "correct": "conversation", "explanation": "Referencing previous contact shows continuity and professional follow-through."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Error Detection and Revision",
                "description": "Students identify and correct deliberate errors in format, tone, and grammar in sample correspondence.",
                "instructions": "1. Read the error-filled business letter below.\n2. Identify ALL errors: format, tone, grammar, and inappropriate language.\n3. Rewrite the corrected version.",
                "exercises": [
                    {
                        "title": "Spot and Fix Correspondence Errors",
                        "exercise_type": "writing",
                        "instructions": "Read the error-filled letter below, list all errors you find, then rewrite it correctly.",
                        "questions": [
                            {"text": "ERROR-FILLED LETTER:\n'hey Mr jones\nhope ur doing good!! We r writing 2 let u know that ur order #789 is ready. its gonna arrive soon so get ready. we need payment asap or we cant send it. lol anyway let us know if u have ?s\nthanks\njohn'\n\nList all errors you find, then rewrite this as a professional business letter.", "explanation": "Errors include: informal greeting, text speak, vague delivery information, demanding tone, inappropriate humour, no reference number structure, missing complimentary close, and unprofessional sign-off."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 13, "title": "Networking and Small Talk",
        "category": "communication", "level": "Intermediate to Advanced",
        "duration": "60–75 min",
        "materials": "Conversation starter cards, professional event scenario descriptions, name badges",
        "objective": "Students develop confidence in initiating and maintaining professional small talk, introducing themselves, and building rapport at business events.",
        "icon_class": "fas fa-comments", "color_class": "teal",
        "subactivities": [
            {
                "order": 1, "title": "Conversation Starter Bank",
                "description": "Brainstorm and categorise appropriate small talk topics for business settings and topics to avoid.",
                "instructions": "1. Review the list of conversation topics.\n2. Sort each into: Appropriate for networking OR Topics to avoid.\n3. Practise opening lines and follow-up questions.",
                "exercises": [
                    {
                        "title": "Appropriate Networking Topics MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Identify which topics are appropriate for professional networking small talk.",
                        "questions": [
                            {"text": "Which topic is MOST appropriate for starting small talk at a business networking event?", "a": "Your political beliefs", "b": "How much you earn", "c": "An interesting industry trend you read about", "d": "A colleague's personal problems", "correct": "c", "explanation": "Industry trends are safe, relevant, and show professional interest — ideal for networking conversations."},
                            {"text": "Which of the following is a strong networking opening line?", "a": "'So, what do you do?'", "b": "'Have you attended this type of event before? What brings you here today?'", "c": "'I hate these events, don't you?'", "d": "'How old are you?'", "correct": "b", "explanation": "Open-ended questions that show genuine interest ('what brings you here?') are more engaging than closed questions."},
                            {"text": "When networking, the best way to end a conversation graciously is:", "a": "'I have to go now. Bye.'", "b": "'You're boring me. I'll find someone else to talk to.'", "c": "'It's been great chatting. I'll let you mingle — shall we exchange cards before I go?'", "d": "'I need to use the bathroom.'", "correct": "c", "explanation": "A graceful exit acknowledges the conversation positively and ends with a concrete next step (exchanging contacts)."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Networking Event Simulation",
                "description": "Classroom set up as a conference reception. Students circulate with fictional name badges and connect with at least 5 people in 15 minutes.",
                "instructions": "1. Put on your name badge with your fictional role and company.\n2. Circulate and introduce yourself to at least 5 different people.\n3. Use conversation starters from Sub-Activity 1.\n4. Note: who you spoke to, their role, and one thing you learned about them.",
                "exercises": [
                    {
                        "title": "Networking Language Fill-in-the-Blank",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete these professional networking phrases with the correct word.",
                        "questions": [
                            {"text": "To introduce yourself: 'Hi, I'm Sarah. I work in ___ development at TechCorp.'", "correct": "business", "explanation": "State your name, function, and company clearly when meeting someone new."},
                            {"text": "To show interest: 'That's fascinating. Could you tell me ___ about what that involves?'", "correct": "more", "explanation": "'Tell me more' is a powerful active listening phrase that encourages the other person to continue."},
                            {"text": "To exchange contacts: 'It's been great ___ to you. Shall we connect on LinkedIn?'", "correct": "talking", "explanation": "Ending on a connection request ensures the conversation leads to a lasting professional relationship."},
                            {"text": "To reference a conversation topic: 'I read a great article about AI in ___ last week. Have you seen any changes in your industry?'", "correct": "finance", "explanation": "Referencing current topics shows you are informed and gives the other person something specific to respond to."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Follow-Up Connection",
                "description": "Students write a brief follow-up email or LinkedIn message to one person they met at the networking event.",
                "instructions": "1. Choose one person from your networking simulation.\n2. Write a professional follow-up email referencing your conversation.\n3. Express interest and suggest a clear next step.",
                "exercises": [
                    {
                        "title": "Write a Networking Follow-Up",
                        "exercise_type": "writing",
                        "instructions": "Write a professional follow-up email or LinkedIn message to someone you met at the networking event.",
                        "questions": [
                            {"text": "Write a networking follow-up message (80–120 words) to [Name], Head of Marketing at [Company], whom you met at the Business Leaders Conference. You discussed the growing use of AI in marketing. Reference the conversation, express genuine interest, and propose a specific next step (e.g., coffee meeting, sharing a resource, connecting on LinkedIn).", "explanation": "Structure: Personal greeting → Reference conversation topic → Specific follow-up → Clear next step → Professional close. Avoid being generic — mention something specific they said."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 14, "title": "Handling Complaints and Conflict Resolution",
        "category": "communication", "level": "Intermediate to Advanced",
        "duration": "75–90 min",
        "materials": "Complaint scenario cards, response templates, empathy phrase bank",
        "objective": "Students learn to handle customer or colleague complaints professionally, using empathy, problem-solving language, and resolution strategies.",
        "icon_class": "fas fa-shield-alt", "color_class": "danger",
        "subactivities": [
            {
                "order": 1, "title": "Empathy and Acknowledgment Training",
                "description": "Teach the acknowledge-apologise-act framework with empathy phrases.",
                "instructions": "1. Study the Acknowledge-Apologise-Act (AAA) framework.\n2. Learn the empathy phrase bank.\n3. Practise responding to sample complaints using these structures.",
                "exercises": [
                    {
                        "title": "Empathy Phrases Matching",
                        "exercise_type": "matching",
                        "instructions": "Match each complaint situation with the most appropriate empathy response.",
                        "questions": [
                            {"left": "Customer: 'I've been waiting 3 weeks for my order!'", "right": "'I completely understand your frustration and sincerely apologise for the delay. Let me look into this immediately.'", "correct": "'I completely understand your frustration and sincerely apologise for the delay. Let me look into this immediately.'"},
                            {"left": "Colleague: 'You never listen to my ideas in meetings.'", "right": "'I appreciate you bringing this to my attention. I can see that hasn't felt fair, and I want to make sure your contributions are recognised.'", "correct": "'I appreciate you bringing this to my attention. I can see that hasn't felt fair, and I want to make sure your contributions are recognised.'"},
                            {"left": "Client: 'The quality of this report is not what we agreed.'", "right": "'You're absolutely right to raise this concern. I take full responsibility and will ensure it is corrected to the standard you expect.'", "correct": "'You're absolutely right to raise this concern. I take full responsibility and will ensure it is corrected to the standard you expect.'"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Escalation Role Play",
                "description": "Multi-stage complaint scenarios where initial response doesn't satisfy. Students adapt and escalate appropriately.",
                "instructions": "1. Role-play the complaint scenario — one partner is the customer, one is the service representative.\n2. Stage 1: Initial response (customer still unhappy).\n3. Stage 2: Escalate, offer alternatives, maintain professionalism.\n4. Switch roles and repeat with a new scenario.",
                "exercises": [
                    {
                        "title": "Complaint Handling Language MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Choose the most professional response for each complaint scenario.",
                        "questions": [
                            {"text": "A customer says: 'I want to speak to your manager NOW!' The best response is:", "a": "'My manager is busy. You'll have to wait.'", "b": "'I understand you'd like to escalate this. I'll connect you with my manager immediately. May I briefly explain the situation to them first?'", "c": "'I am the manager.'", "d": "'There's nothing my manager can do differently.'", "correct": "b", "explanation": "Acknowledging the escalation request, acting promptly, and briefing the manager shows professionalism and efficiency."},
                            {"text": "When you cannot immediately solve a complaint, the best approach is to:", "a": "Apologise repeatedly without offering solutions", "b": "Blame company policy", "c": "Acknowledge the issue, commit to a specific action and timeline, and follow up", "d": "Transfer the customer to another department without explanation", "correct": "c", "explanation": "Committing to a specific action with a clear timeline shows accountability and builds trust, even when an immediate fix is unavailable."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Written Complaint Response",
                "description": "Students draft formal written responses to complaint letters or emails.",
                "instructions": "1. Read the customer complaint email below.\n2. Draft a formal written response using the AAA framework.\n3. Include: acknowledgement, explanation, solution, follow-up offer.",
                "exercises": [
                    {
                        "title": "Write a Complaint Response",
                        "exercise_type": "writing",
                        "instructions": "Write a professional complaint response email to the customer complaint below.",
                        "questions": [
                            {"text": "CUSTOMER COMPLAINT: 'Dear Customer Service, I placed order #8821 on 1st March and was promised delivery within 5 working days. It is now 20th March and I have received nothing. I have called three times and been told different things each time. This is completely unacceptable. I want a full refund and an explanation. — Mrs T. Brown'\n\nWrite a formal complaint response (150–200 words) using the Acknowledge-Apologise-Act framework.", "explanation": "Structure: 1) Address by name 2) Acknowledge the problem and apologise sincerely 3) Provide brief explanation (without excuses) 4) State specific resolution (refund timeline, tracking info) 5) Offer additional support 6) Professional close."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 15, "title": "Business Vocabulary Building Games",
        "category": "vocabulary", "level": "Pre-Intermediate to Upper-Intermediate",
        "duration": "45–60 min",
        "materials": "Vocabulary cards, buzzword bingo sheets, industry glossaries, timer",
        "objective": "Students expand and reinforce business vocabulary through competitive, interactive games that promote active recall and contextual usage.",
        "icon_class": "fas fa-puzzle-piece", "color_class": "warning",
        "subactivities": [
            {
                "order": 1, "title": "Industry Jargon Relay",
                "description": "Teams list as many relevant terms as possible per business category in 3 minutes.",
                "instructions": "1. Your team will be assigned a business category.\n2. In 3 minutes, list as many relevant business terms as you can.\n3. Bonus points for correct definitions and example sentences.\n4. Rotate to the next category for another round.",
                "exercises": [
                    {
                        "title": "Business Vocabulary MCQ Challenge",
                        "exercise_type": "mcq",
                        "instructions": "Select the correct meaning for each business term. Score points for each correct answer!",
                        "questions": [
                            {"text": "'Synergy' in a business context means:", "a": "A type of energy drink popular in offices", "b": "The combined effect of two entities working together is greater than the sum of their individual efforts", "c": "A financial loss", "d": "A disagreement between departments", "correct": "b", "explanation": "Synergy describes how combining resources, teams, or companies creates more value than they would separately."},
                            {"text": "'Scalable' (as in 'a scalable business model') means:", "a": "The business has a weighing scale", "b": "The business can grow significantly without proportional increase in costs", "c": "The product is sold by weight", "d": "The company is very small", "correct": "b", "explanation": "A scalable business can handle increased demand without dramatically increasing costs — key for investors."},
                            {"text": "'KPI' stands for:", "a": "Key Profit Index", "b": "Key Performance Indicator", "c": "Knowledge and Progress Insight", "d": "Key Pricing Incentive", "correct": "b", "explanation": "KPIs are measurable values that show how effectively a company is achieving its business objectives."},
                            {"text": "'Disruptive innovation' refers to:", "a": "A product recall", "b": "An innovation that displaces established products and changes entire industries", "c": "When office equipment breaks down", "d": "A disagreement about product design", "correct": "b", "explanation": "Coined by Clayton Christensen — disruptive innovations (e.g., Uber, Airbnb) fundamentally change how industries operate."},
                            {"text": "'B2B' stands for:", "a": "Business to Bank", "b": "Budget to Budget", "c": "Business to Business", "d": "Brand to Brand", "correct": "c", "explanation": "B2B describes commerce between businesses (e.g., a software company selling to corporations) vs. B2C (Business to Consumer)."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Buzzword Bingo",
                "description": "Students match spoken definitions to the correct business buzzword on a 5×5 card and aim for a bingo.",
                "instructions": "1. Your card is a 5×5 grid of 25 business buzzwords.\n2. Press Start. For each round a definition is shown and read aloud — the word itself is hidden.\n3. Click the word that matches the definition (your pick turns blue). You must pick a word before moving on.\n4. After the last word, every pick is graded — green for correct, red for incorrect — and your score is shown.\n5. Get 5 correct answers in a row, column, or diagonal to score a BINGO!",
                "exercises": [
                    {
                        "title": "Business Buzzword Bingo",
                        "exercise_type": "bingo",
                        "instructions": "Press 'Start Game'. Read/listen to each definition and click the matching word, then 'Next Word'. Correct answers fill your 5×5 card — get 5 in a row, column, or diagonal for a BINGO! Picks are graded at the end and your score is shown.",
                        "bingo_words": [
                            ("Synergy", "When combined efforts produce greater results than individual ones"),
                            ("Scalable", "Able to grow without proportional cost increases"),
                            ("Pivot", "To change business direction or strategy in response to market feedback"),
                            ("Disruptive", "Radically changing an industry by introducing new technology or methods"),
                            ("Agile", "A flexible, iterative approach to project management and development"),
                            ("ROI", "Return on Investment — profit relative to cost"),
                            ("Bandwidth", "Used figuratively to mean available time or capacity"),
                            ("Leverage", "Using resources to maximise advantage or returns"),
                            ("Stakeholder", "Anyone with an interest or investment in a business outcome"),
                            ("Pipeline", "Future deals, projects, or opportunities in development"),
                            ("Deliverable", "A tangible output or result that must be produced"),
                            ("Benchmark", "A standard point of reference used for comparison"),
                            ("Holistic", "Considering all aspects of something together rather than separately"),
                            ("Onboarding", "The process of integrating a new employee or customer"),
                            ("Value-add", "Something that provides additional benefit beyond the basic offering"),
                            ("Circle back", "To return to a topic or conversation at a later time"),
                            ("Low-hanging fruit", "Easy wins or quick gains that can be achieved with minimal effort"),
                            ("Move the needle", "To make a significant impact or progress on something"),
                            ("Touch base", "To make brief contact to check in or update someone"),
                            ("Boil the ocean", "To attempt an overly ambitious or impossible task"),
                            ("Deep dive", "A thorough, detailed analysis of a topic"),
                            ("Thought leader", "An expert or innovator whose ideas are highly influential"),
                            ("Core competency", "A company's primary area of expertise or strength"),
                            ("Bleeding edge", "More advanced than cutting-edge — often implies risk"),
                            ("Runway", "The amount of time a company can operate before running out of money"),
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Context Clue Challenge",
                "description": "Students identify missing vocabulary from context and create original sentences.",
                "instructions": "1. Read each sentence carefully.\n2. Identify the missing business vocabulary word from context.\n3. After the quiz, create 3 original sentences using newly learned terms.",
                "exercises": [
                    {
                        "title": "Business Vocabulary Context Clues",
                        "exercise_type": "fill_blank",
                        "instructions": "Use context clues to fill in the missing business vocabulary word in each sentence.",
                        "questions": [
                            {"text": "The startup had impressive technology but lacked the ___ to deliver at scale — they simply didn't have enough people or systems.", "correct": "bandwidth", "explanation": "'Bandwidth' is used figuratively in business to mean available capacity — people, time, or resources."},
                            {"text": "After three failed product launches, the CEO decided to ___ and focus on a completely different market segment.", "correct": "pivot", "explanation": "'Pivot' means to change direction strategically in response to what the market is telling you."},
                            {"text": "Rather than tackle the entire backlog at once, the team decided to start with the ___ fruit — quick tasks they could complete in one afternoon.", "correct": "low-hanging", "explanation": "'Low-hanging fruit' refers to the easiest, most accessible opportunities or tasks."},
                            {"text": "Let's ___ back to the budget discussion after lunch — we need the finance team to be present.", "correct": "circle", "explanation": "'Circle back' means to return to a topic at a later point in time."},
                            {"text": "The new software platform is highly ___ — it currently serves 500 users but can support 50,000 with no major infrastructure changes.", "correct": "scalable", "explanation": "'Scalable' means the system can grow without proportional increases in cost or complexity."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 16, "title": "Proposal and Bid Writing",
        "category": "writing", "level": "Upper-Intermediate to Advanced",
        "duration": "120–150 min",
        "materials": "Request for Proposal (RFP) documents, proposal templates, evaluation criteria",
        "objective": "Students learn to write persuasive, structured business proposals in response to a client brief, including executive summaries, deliverables, timelines, and pricing.",
        "icon_class": "fas fa-file-contract", "color_class": "indigo",
        "subactivities": [
            {
                "order": 1, "title": "RFP Analysis and Planning",
                "description": "Students analyse an RFP document and plan their proposal response.",
                "instructions": "1. Read the Request for Proposal (RFP) document carefully.\n2. Identify: client needs, evaluation criteria, submission requirements, and key deadlines.\n3. Brainstorm your proposed solution and assign writing responsibilities.\n4. Identify your win themes and key differentiators.",
                "exercises": [
                    {
                        "title": "RFP Analysis MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Test your knowledge of proposal writing and RFP analysis.",
                        "questions": [
                            {"text": "The primary purpose of an executive summary in a business proposal is:", "a": "To list all team members", "b": "To give a brief, compelling overview of your solution that can stand alone", "c": "To provide detailed pricing tables", "d": "To describe your company history", "correct": "b", "explanation": "The executive summary is often read first and sometimes alone — it must be compelling enough to motivate the reader to continue."},
                            {"text": "A 'win theme' in proposal writing is:", "a": "A catchy headline for your company logo", "b": "A key message that differentiates you from competitors and speaks directly to client needs", "c": "A celebration when you win the contract", "d": "The financial section of the proposal", "correct": "b", "explanation": "Win themes are repeated throughout the proposal to reinforce your value proposition and differentiation."},
                            {"text": "When responding to an RFP, the most important first step is:", "a": "Writing the executive summary", "b": "Setting your pricing", "c": "Thoroughly reading the RFP to understand evaluation criteria", "d": "Designing the cover page", "correct": "c", "explanation": "Understanding exactly what the client is evaluating helps you tailor every section of your proposal to score highly."},
                            {"text": "Persuasive language in a proposal is characterised by:", "a": "Vague promises and general statements", "b": "Evidence-based claims, specific outcomes, and client-focused language", "c": "Technical jargon to impress the reader", "d": "First-person casual writing", "correct": "b", "explanation": "Effective proposals use specific evidence (case studies, data, testimonials) and focus on client outcomes rather than company features."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Collaborative Proposal Drafting",
                "description": "Each group member writes their assigned section, then the group assembles a complete proposal.",
                "instructions": "1. Each team member writes their assigned section: Executive Summary, Technical Approach, Team Qualifications, Timeline, or Pricing.\n2. Assemble sections ensuring consistent tone and formatting.\n3. Review for persuasive language and evidence-based claims.",
                "exercises": [
                    {
                        "title": "Proposal Section Writing",
                        "exercise_type": "writing",
                        "instructions": "Write your assigned proposal section based on the RFP brief provided.",
                        "questions": [
                            {"text": "RFP BRIEF: A regional hospital seeks a vendor to implement a new patient appointment scheduling system. Key requirements: 24/7 online booking, integration with existing EHR system, staff training included, go-live within 6 months, budget £80K–£120K.\n\nWrite the Executive Summary section (150–200 words) for your proposal responding to this RFP.", "explanation": "Executive Summary must: name the client and their need, state your solution in one sentence, highlight 2–3 differentiators, reference your track record, end with a confident closing statement."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Proposal Defence Presentation",
                "description": "Groups present their proposal to a client evaluation panel. Panel scores each proposal.",
                "instructions": "1. Prepare a 10-minute proposal defence presentation.\n2. Be ready to answer questions on methodology, pricing, and capability.\n3. Use the 60-second timer to practise your key sections.",
                "exercises": [
                    {
                        "title": "Proposal Presentation Timer",
                        "exercise_type": "timer",
                        "instructions": "Use the timer to practise each key section of your proposal defence presentation.",
                        "questions": [
                            {"text": "Executive Summary: Deliver your proposal overview — problem, solution, and why you.", "explanation": "60 seconds. Be confident and client-focused. No reading from notes."},
                            {"text": "Technical Approach: Explain HOW your solution will be implemented, step by step.", "explanation": "Focus on clarity and feasibility. Anticipate 'how will you handle...' questions."},
                            {"text": "Pricing Justification: Explain your pricing clearly and why the investment delivers value.", "explanation": "Never apologise for your price. Link every cost to a client benefit."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 17, "title": "Data Presentation and Visualization",
        "category": "analysis", "level": "Intermediate to Advanced",
        "duration": "60–90 min",
        "materials": "Data sets, chart creation tools, language reference for describing trends",
        "objective": "Students practice describing data, trends, and charts using accurate business English, and learn to choose appropriate visualizations for different data types.",
        "icon_class": "fas fa-chart-bar", "color_class": "primary",
        "subactivities": [
            {
                "order": 1, "title": "Trend Description Language",
                "description": "Teach vocabulary and structures for describing data trends. Students build a personal phrase bank.",
                "instructions": "1. Study the trend language phrase bank.\n2. Match each phrase to its correct movement type.\n3. Practise describing 3 sample charts using the language.",
                "exercises": [
                    {
                        "title": "Trend Language Matching",
                        "exercise_type": "matching",
                        "instructions": "Match each trend description phrase to the correct data movement it describes.",
                        "questions": [
                            {"left": "'Rose sharply' / 'Surged' / 'Jumped'", "right": "Rapid upward movement", "correct": "Rapid upward movement"},
                            {"left": "'Declined gradually' / 'Fell steadily' / 'Dropped'", "right": "Downward movement", "correct": "Downward movement"},
                            {"left": "'Remained stable' / 'Held steady' / 'Plateaued'", "right": "No significant change", "correct": "No significant change"},
                            {"left": "'Fluctuated between' / 'Varied'", "right": "Irregular movement up and down", "correct": "Irregular movement up and down"},
                            {"left": "'Peaked at' / 'Reached a high of'", "right": "Reached the highest point", "correct": "Reached the highest point"},
                            {"left": "'Hit a low of' / 'Bottomed out at'", "right": "Reached the lowest point", "correct": "Reached the lowest point"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Chart Interpretation Challenge",
                "description": "Students write short paragraphs describing 5–6 different chart types and compare interpretations.",
                "instructions": "1. Study the 3 chart descriptions below.\n2. Write a one-paragraph interpretation for each.\n3. Include: the main trend, a notable data point, and one conclusion.",
                "exercises": [
                    {
                        "title": "Choosing the Right Chart Type",
                        "exercise_type": "mcq",
                        "instructions": "Select the best chart type for each data presentation scenario.",
                        "questions": [
                            {"text": "You want to show market share distribution among 5 competitors as percentages of a whole. The best chart type is:", "a": "Line chart", "b": "Bar chart", "c": "Pie chart", "d": "Scatter plot", "correct": "c", "explanation": "Pie charts are ideal for showing parts of a whole, especially when you have a small number of categories."},
                            {"text": "You want to show how monthly revenue has changed over a 12-month period. The best chart type is:", "a": "Pie chart", "b": "Line chart", "c": "Pie chart", "d": "Heat map", "correct": "b", "explanation": "Line charts show change over time most clearly, making trends easy to see."},
                            {"text": "You want to compare quarterly performance across 4 different product lines. The best chart type is:", "a": "Scatter plot", "b": "Grouped bar chart", "c": "Pie chart", "d": "Line chart", "correct": "b", "explanation": "Grouped (clustered) bar charts allow direct comparison across multiple categories."},
                            {"text": "You want to show the correlation between advertising spend and sales revenue. The best chart type is:", "a": "Pie chart", "b": "Bar chart", "c": "Scatter plot", "d": "Heat map", "correct": "c", "explanation": "Scatter plots reveal correlations and relationships between two variables."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Data Storytelling Presentation",
                "description": "Each student creates 2–3 visualisations from a dataset and delivers a 3-minute data story.",
                "instructions": "1. Receive your dataset and create 2–3 key visualisations.\n2. Craft a 3-minute narrative explaining the key insights.\n3. Use the trend language from Sub-Activity 1.\n4. Practise with the timer below.",
                "exercises": [
                    {
                        "title": "Data Story Presentation Timer",
                        "exercise_type": "timer",
                        "instructions": "Use the timer to practise each section of your data story presentation.",
                        "questions": [
                            {"text": "Opening: State the key finding in one sentence before showing any charts — the 'so what' first.", "explanation": "Lead with insight, not data. E.g., 'Our customer satisfaction has improved dramatically, and here's why.'"},
                            {"text": "Chart Walk-Through: Describe each chart clearly using trend language. Explain what each data point means in business terms.", "explanation": "Don't just say what the chart shows — explain what it MEANS for the business."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 18, "title": "Business Idioms and Phrasal Verbs",
        "category": "vocabulary", "level": "Intermediate to Upper-Intermediate",
        "duration": "45–60 min",
        "materials": "Idiom flashcards, context sentences, matching worksheets, quiz templates",
        "objective": "Students learn, practice, and actively use common business idioms and phrasal verbs in realistic professional contexts.",
        "icon_class": "fas fa-language", "color_class": "purple",
        "subactivities": [
            {
                "order": 1, "title": "Idiom Discovery and Matching",
                "description": "Present 15–20 business idioms. Students match idioms to definitions and example sentences.",
                "instructions": "1. Study the business idioms in the list below.\n2. Match each idiom to its correct definition.\n3. Discuss literal vs. figurative meanings with a partner.",
                "exercises": [
                    {
                        "title": "Business Idioms Matching Game",
                        "exercise_type": "matching",
                        "instructions": "Match each business idiom on the left to its correct meaning on the right. Click to select and connect them.",
                        "questions": [
                            {"left": "Cut corners", "right": "To do something the easy or cheap way, sacrificing quality", "correct": "To do something the easy or cheap way, sacrificing quality"},
                            {"left": "Think outside the box", "right": "To think creatively and consider unconventional solutions", "correct": "To think creatively and consider unconventional solutions"},
                            {"left": "Get the ball rolling", "right": "To start a process or activity", "correct": "To start a process or activity"},
                            {"left": "The bottom line", "right": "The most important point or the final financial result", "correct": "The most important point or the final financial result"},
                            {"left": "Back to the drawing board", "right": "To start again from the beginning because the plan failed", "correct": "To start again from the beginning because the plan failed"},
                            {"left": "Hit the ground running", "right": "To start something quickly and energetically without delay", "correct": "To start something quickly and energetically without delay"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Phrasal Verb Role Play",
                "description": "Students role-play business scenarios that naturally require specific phrasal verbs.",
                "instructions": "1. Read the business scenarios below.\n2. Role-play each scenario naturally incorporating the target phrasal verbs.\n3. Your partner checks off each phrasal verb as you use it correctly.",
                "exercises": [
                    {
                        "title": "Phrasal Verbs Fill-in-the-Blank",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete each sentence with the correct phrasal verb from the box: set up, follow up, carry out, take over, wrap up, draw up.",
                        "questions": [
                            {"text": "Could you please ___ ___ on the proposal we sent last week? We haven't heard back from the client.", "correct": "follow up", "explanation": "'Follow up' means to contact someone again to check on progress or get a response."},
                            {"text": "The team needs to ___ ___ the research before we can make any decisions.", "correct": "carry out", "explanation": "'Carry out' means to perform or execute a task or plan."},
                            {"text": "Sarah will ___ ___ the project while the manager is on leave.", "correct": "take over", "explanation": "'Take over' means to assume responsibility or control of something."},
                            {"text": "Let's ___ ___ a meeting with the stakeholders for next Tuesday.", "correct": "set up", "explanation": "'Set up' means to arrange or organise something."},
                            {"text": "The lawyer will ___ ___ the contract once we agree on the final terms.", "correct": "draw up", "explanation": "'Draw up' means to prepare a formal document such as a contract or plan."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Idiom Story Challenge",
                "description": "Each student draws 3–4 idiom cards and writes a business scenario incorporating all of them naturally.",
                "instructions": "1. Select 4 idioms from the list below.\n2. Write a short business scenario (100–150 words) that uses all 4 idioms naturally and in the correct context.\n3. Read your story aloud — classmates vote on the most creative and contextually accurate use.",
                "exercises": [
                    {
                        "title": "Write a Business Idiom Story",
                        "exercise_type": "writing",
                        "instructions": "Write a 120–150 word business scenario naturally incorporating the 4 idioms listed below.",
                        "questions": [
                            {"text": "Use ALL FOUR of these idioms naturally in a coherent business story or situation:\n1. 'hit the ground running'\n2. 'back to the drawing board'\n3. 'think outside the box'\n4. 'get the ball rolling'\n\nYour story should read naturally — idioms must feel genuine, not forced.", "explanation": "Tip: Build a simple narrative (e.g., a new project, product launch, or team challenge) where each idiom fits naturally into the flow of events."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 19, "title": "Corporate Social Responsibility Debate",
        "category": "speaking", "level": "Upper-Intermediate to Advanced",
        "duration": "75–90 min",
        "materials": "CSR case studies, debate format guide, argument structure handout",
        "objective": "Students research, argue, and debate corporate social responsibility topics using formal argumentation language, persuasive techniques, and evidence-based reasoning.",
        "icon_class": "fas fa-balance-scale", "color_class": "success",
        "subactivities": [
            {
                "order": 1, "title": "Argumentation Language Workshop",
                "description": "Teach formal debate language: stating positions, presenting evidence, rebutting, and concluding.",
                "instructions": "1. Study the formal debate language bank.\n2. Categorise phrases by function: Stating Position, Presenting Evidence, Rebutting, Conceding, Concluding.\n3. Practise using each phrase in a short argument.",
                "exercises": [
                    {
                        "title": "Debate Language Matching",
                        "exercise_type": "matching",
                        "instructions": "Match each debate language phrase to its correct function in a formal argument.",
                        "questions": [
                            {"left": "'We firmly believe that companies have a responsibility to...'", "right": "Stating your position", "correct": "Stating your position"},
                            {"left": "'Research from the UN demonstrates that...'", "right": "Presenting evidence", "correct": "Presenting evidence"},
                            {"left": "'While my opponent argues that X, the evidence actually shows...'", "right": "Rebutting the opposing view", "correct": "Rebutting the opposing view"},
                            {"left": "'We acknowledge that there is merit to the point about...'", "right": "Conceding a point gracefully", "correct": "Conceding a point gracefully"},
                            {"left": "'In light of these arguments, it is clear that...'", "right": "Drawing a conclusion", "correct": "Drawing a conclusion"},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Research and Position Building",
                "description": "Teams research their assigned CSR debate position and prepare opening statements, key arguments, and rebuttals.",
                "instructions": "1. Read your assigned debate position on the CSR topic.\n2. Research 3 strong arguments with supporting evidence.\n3. Anticipate 2 counter-arguments and prepare rebuttals.\n4. Write your opening statement (2 minutes / ~280 words).",
                "exercises": [
                    {
                        "title": "CSR Debate Positions MCQ",
                        "exercise_type": "mcq",
                        "instructions": "Test your understanding of key CSR concepts and debate positions.",
                        "questions": [
                            {"text": "The 'triple bottom line' in CSR refers to:", "a": "Three consecutive financial losses", "b": "Measuring business success across People, Planet, and Profit", "c": "Three levels of corporate tax", "d": "The three founders of CSR theory", "correct": "b", "explanation": "The triple bottom line (3Ps) framework measures a company's social, environmental, and economic impact — not just profit."},
                            {"text": "Milton Friedman's classic argument about business and social responsibility states that:", "a": "Companies should donate 10% of profits to charity", "b": "The social responsibility of business is to increase its profits within legal rules", "c": "All businesses must have a CSR department", "d": "Companies should prioritise environmental impact over profits", "correct": "b", "explanation": "Friedman (1970) argued that a company's primary duty is to shareholders and profit — CSR beyond legal requirements is a misuse of shareholder money."},
                            {"text": "Which argument best SUPPORTS mandatory CSR for large corporations?", "a": "CSR reduces short-term profits which harms shareholders", "b": "Companies with strong CSR perform better long-term and attract talent", "c": "CSR should be entirely voluntary", "d": "Only governments should address social issues", "correct": "b", "explanation": "Research shows strong ESG (Environmental, Social, Governance) companies outperform peers long-term and attract top talent."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Structured Debate and Evaluation",
                "description": "Run a formal debate with timed rounds. Non-debating students score using criteria rubric.",
                "instructions": "1. Follow the debate format: Opening (2 min each) → Arguments (3 rounds × 2 min) → Rebuttals (2 min each) → Closing (1 min each).\n2. Non-debating students score using the rubric: argument quality, evidence, language, persuasiveness.\n3. Write a reflection on the opposing side's strongest argument.",
                "exercises": [
                    {
                        "title": "Debate Performance Writing",
                        "exercise_type": "writing",
                        "instructions": "Write a structured post-debate reflection on the CSR debate experience.",
                        "questions": [
                            {"text": "Write a 150–200 word post-debate reflection addressing:\n1. What was the opposing team's strongest argument and why?\n2. Which piece of evidence you presented was most effective and why?\n3. How effectively did you use formal debate language (citing 2 specific phrases you used)?", "explanation": "Be specific and analytical — reference actual arguments made during the debate. This demonstrates critical thinking, not just general reflection."},
                        ]
                    },
                ]
            },
        ]
    },
    {
        "order": 20, "title": "Project Status Update and Reporting",
        "category": "communication", "level": "Intermediate to Advanced",
        "duration": "60–90 min",
        "materials": "Project status templates, milestone trackers, progress report examples",
        "objective": "Students practice delivering clear, structured project status updates using appropriate language for reporting progress, flagging risks, and requesting support.",
        "icon_class": "fas fa-tasks", "color_class": "success",
        "subactivities": [
            {
                "order": 1, "title": "Status Update Structure and Language",
                "description": "Introduce the standard status update format: accomplishments, upcoming tasks, blockers, and requests.",
                "instructions": "1. Study the 4-part status update format: Accomplishments → Upcoming → Blockers → Requests.\n2. Complete the fill-in-the-blank status update language exercise.\n3. Practise the format with a partner using the sample scenario.",
                "exercises": [
                    {
                        "title": "Status Update Language Fill-in-the-Blank",
                        "exercise_type": "fill_blank",
                        "instructions": "Complete each project status update phrase with the correct word.",
                        "questions": [
                            {"text": "To report being on schedule: 'We're on ___ to meet the deadline as planned.'", "correct": "track", "explanation": "'On track' is the standard phrase meaning progress is proceeding as planned."},
                            {"text": "To flag a delay: 'We've ___ a delay in the testing phase due to resource constraints.'", "correct": "encountered", "explanation": "'Encountered a delay/issue' is professional language for reporting problems without assigning blame."},
                            {"text": "To request support: 'We'd ___ additional support from the IT team to resolve the server issue.'", "correct": "appreciate", "explanation": "'We'd appreciate' is a polite way to request help without demanding it."},
                            {"text": "To summarise accomplishments: 'This week, we successfully ___ Phase 2 of the project, including all deliverables.'", "correct": "completed", "explanation": "'Successfully completed' confirms achievement clearly and professionally."},
                            {"text": "To describe a risk: 'The ___ risk is a potential delay in vendor delivery, which could impact our go-live date.'", "correct": "primary", "explanation": "Identifying the 'primary risk' focuses attention on the most critical issue."},
                        ]
                    },
                ]
            },
            {
                "order": 2, "title": "Written Status Report Drafting",
                "description": "Students write a one-page status report from a fictional project scenario.",
                "instructions": "1. Read the fictional project scenario provided.\n2. Write a one-page status report using the 4-part template.\n3. Focus on: concise language, factual reporting, and clear action items with owners and deadlines.",
                "exercises": [
                    {
                        "title": "Write a Project Status Report",
                        "exercise_type": "writing",
                        "instructions": "Write a professional project status report based on the scenario below.",
                        "questions": [
                            {"text": "PROJECT SCENARIO: You are PM for 'Project Horizon' — a website redesign for a retail client due 30 June. It's currently 15 May.\n\nCompleted: UX design (approved), content migration (80%), dev sprint 1.\nIn Progress: Dev sprint 2, client review of homepage mock-ups.\nBlocker: Client has not provided product images for 15 pages — delaying sprint 3 start by estimated 1 week.\nNext steps: Chase client for images, begin sprint 3 non-image pages.\n\nWrite the full status report (150–200 words) using the Accomplishments-Upcoming-Blockers-Requests format.", "explanation": "Each section needs specific facts and dates. Action items must have: what, who, by when. Tone: factual, professional, solution-focused."},
                        ]
                    },
                ]
            },
            {
                "order": 3, "title": "Stand-Up Meeting Simulation",
                "description": "Simulate a team stand-up where each student delivers a 2-minute verbal update. Project manager asks clarifying questions.",
                "instructions": "1. Prepare your 2-minute verbal status update from your written report.\n2. Deliver it clearly: Accomplished → Upcoming → Blockers → Requests.\n3. The rotating Project Manager asks 2 clarifying questions.\n4. Use the timer to keep to 2 minutes.",
                "exercises": [
                    {
                        "title": "Stand-Up Update Timer",
                        "exercise_type": "timer",
                        "instructions": "Use this timer to practise your 60-second verbal project status update. Be concise — cover all 4 sections.",
                        "questions": [
                            {"text": "Deliver your complete status update: Accomplished, Upcoming, Blockers, and Requests — all in 60 seconds.", "explanation": "Time-box yourself. Remove any information that doesn't directly affect decisions. Cut filler words ('basically', 'kind of', 'sort of')."},
                            {"text": "Answer a tough Project Manager question: 'If the images don't arrive by Friday, what is your contingency plan?'", "explanation": "A strong answer: states a specific alternative action, confirms the risk it avoids, and gives a revised timeline if needed."},
                        ]
                    },
                ]
            },
        ]
    },
]

ACTIVITY_COLORS = [
    'primary', 'success', 'info', 'warning', 'purple',
    'danger', 'teal', 'orange', 'rose', 'emerald',
    'indigo', 'pink', 'teal', 'danger', 'warning',
    'indigo', 'primary', 'purple', 'success', 'success',
]


# Interactive Workshop activities. These are `category='workshop'` and have no
# sub-activities/exercises of their own — opening one redirects to its dedicated
# app (see activities.views.get_workshop_url / workshop_dashboard, which match on
# these exact titles). Seeding them here means a fresh environment always has
# Group Discussion, JAM and Role Play available.
# Orders 1–20 are the Business English activities above; 21–24 are the
# professional AI modules (see setup_professional_modules). Workshops therefore
# start at 25 to avoid colliding with either.
WORKSHOP_ACTIVITIES = [
    {
        "order": 25, "title": "Group Discussion",
        "category": "workshop", "level": "All Levels",
        "duration": "20–30 min",
        "materials": "Microphone, quiet room",
        "objective": "Practise real-time group discussions with three distinct AI participants and receive feedback on your contributions.",
        "icon_class": "fas fa-comments", "color_class": "info",
    },
    {
        "order": 26, "title": "JAM (Just A Minute)",
        "category": "workshop", "level": "All Levels",
        "duration": "10–15 min",
        "materials": "Microphone, quiet room, timer",
        "objective": "Sharpen spontaneous fluency by speaking on a surprise topic for one minute, with AI feedback on pace and clarity.",
        "icon_class": "fas fa-stopwatch", "color_class": "warning",
    },
    {
        "order": 27, "title": "Role Play",
        "category": "workshop", "level": "All Levels",
        "duration": "15–25 min",
        "materials": "Microphone, quiet room",
        "objective": "Rehearse realistic professional scenarios through interactive AI-driven role play and situational practice.",
        "icon_class": "fas fa-user-friends", "color_class": "purple",
    },
]


class Command(BaseCommand):
    help = (
        'Seed all Business English activities, the Interactive Workshop '
        'activities (GD/JAM/Role Play), sub-activities and exercises.\n\n'
        'DEFAULT (safe fill): only CREATES rows that are missing. Never edits, '
        'deletes, or resurrects anything that already exists — so admin edits, '
        'hidden activities (is_active=False) and learner progress are all kept. '
        'Ideal for topping up a fresh or partial database.\n\n'
        'Use --sync to make the seed file authoritative (push content changes '
        'over existing rows), and --prune (with --sync) to remove sub-activities/'
        'exercises no longer in the seed.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help=(
                'Overwrite existing activities/sub-activities/exercises and '
                'rebuild their questions to match the seed file exactly. Learner '
                'progress and is_active are still preserved. Without this flag, '
                'existing rows are left untouched (create-only).'
            ),
        )
        parser.add_argument(
            '--prune',
            action='store_true',
            help=(
                'With --sync, also remove sub-activities/exercises that are no '
                'longer in the seed data. WARNING: pruning cascades to and '
                'deletes the learner progress/scores attached to them.'
            ),
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help=(
                'Skip the interactive confirmation prompt when using --prune. '
                'Required in non-interactive environments (CI/scripts). '
                'DANGER: learner progress will be permanently deleted.'
            ),
        )

    def handle(self, *args, **options):
        sync = options['sync']
        prune = options['prune'] and sync

        if options['prune'] and not sync:
            self.stdout.write(self.style.WARNING(
                '--prune has no effect without --sync; ignoring it.'
            ))

        # Safety gate: --prune deletes UserProgress/UserExerciseResult rows.
        # Require explicit --yes or a typed confirmation before proceeding.
        if prune and not options.get('yes'):
            self.stdout.write(self.style.ERROR(
                '\n[DANGER] --prune will permanently DELETE learner progress '
                '(UserProgress) and exercise results (UserExerciseResult) for '
                'any sub-activities/exercises removed from the seed file.\n'
                'This CANNOT be undone. Type YES to confirm, or anything else to abort: '
            ))
            answer = input('').strip()
            if answer != 'YES':
                self.stdout.write(self.style.WARNING('Aborted. No changes were made.'))
                return

        # deepcopy so the module-level seed data is never mutated by our .pop()s.
        # Without this, a second in-process invocation would abort half-way once
        # the 'subactivities'/'exercises'/'questions' keys had been popped.
        all_activities = copy.deepcopy(ACTIVITIES_DATA) + copy.deepcopy(WORKSHOP_ACTIVITIES)

        mode = 'SYNC (seed file is authoritative)' if sync else 'safe fill (create-only)'
        self.stdout.write(self.style.WARNING(
            f'Seeding activities — mode: {mode}. Learner progress preserved.'
        ))

        created_count = 0
        skipped_count = 0
        updated_count = 0

        with transaction.atomic():
            for act_data in all_activities:
                subactivities_data = act_data.pop('subactivities', [])

                activity, status = self._upsert_activity(act_data, sync)
                created_count += int(status == 'created')
                updated_count += int(status == 'updated')
                skipped_count += int(status == 'skipped')
                self.stdout.write(f'  {status.title()}: Activity {activity.order} – {activity.title}')

                seen_sub_orders = []
                for sub_data in subactivities_data:
                    exercises_data = sub_data.pop('exercises', [])
                    sub, sub_created = self._upsert_subactivity(activity, sub_data, sync)
                    seen_sub_orders.append(sub.order)

                    seen_ex_orders = []
                    for ex_idx, ex_data in enumerate(exercises_data, 1):
                        questions_data = ex_data.pop('questions', [])
                        bingo_words    = ex_data.pop('bingo_words', [])
                        ex_data['order'] = ex_idx

                        exercise, ex_created = self._upsert_exercise(sub, ex_idx, ex_data, sync)
                        seen_ex_orders.append(ex_idx)
                        # Rebuild questions/bingo only for brand-new exercises, or
                        # when --sync makes the seed authoritative. This keeps
                        # admin-edited content intact on a default run.
                        if ex_created or sync:
                            self._replace_questions(exercise, questions_data)
                            self._replace_bingo(exercise, bingo_words)

                    if prune:
                        # Removes exercises dropped from the seed. Cascades to
                        # UserExerciseResult, so it is opt-in only.
                        sub.exercises.exclude(order__in=seen_ex_orders).delete()

                if prune:
                    # Removes sub-activities dropped from the seed. Cascades to
                    # UserProgress, so it is opt-in only.
                    activity.subactivities.exclude(order__in=seen_sub_orders).delete()

        # The four professional AI modules (orders 21-24) are defined in their own
        # command. Run it here so a single populate_activities gives the full
        # catalogue — without it, fresh databases ended up with only 23 activities
        # and the Free Plan was missing Listen & Learn / Professional Reading.
        call_command('setup_professional_modules', create_only=not sync, stdout=self.stdout)

        total   = Activity.objects.count()
        total_subs = SubActivity.objects.count()
        total_ex   = Exercise.objects.count()
        total_q    = Question.objects.count()
        total_b    = BingoCard.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Done! '
            f'{created_count} created, {updated_count} updated, '
            f'{skipped_count} left untouched (already existed).\n'
            f'  {total} Activities (incl. {len(WORKSHOP_ACTIVITIES)} workshops)\n'
            f'  {total_subs} Sub-Activities\n'
            f'  {total_ex} Exercises\n'
            f'  {total_q} Questions\n'
            f'  {total_b} Bingo Cards\n'
        ))

    # --------------------------------------------------------------------- #
    #  Upsert helpers
    #
    #  Natural keys keep row PKs stable, so learner foreign keys (UserProgress,
    #  UserExerciseResult) always survive. `is_active` is never written here, so
    #  an activity hidden via the admin is never resurrected. When sync=False,
    #  existing rows are returned untouched (create-only).
    # --------------------------------------------------------------------- #
    def _upsert_activity(self, act_data, sync):
        """Return (activity, 'created'|'updated'|'skipped'). Keyed on order."""
        existing = Activity.objects.filter(order=act_data['order']).first()
        if existing:
            if sync:
                for field, value in act_data.items():
                    setattr(existing, field, value)
                existing.save()
                return existing, 'updated'
            return existing, 'skipped'
        return Activity.objects.create(**act_data), 'created'

    def _upsert_subactivity(self, activity, sub_data, sync):
        """Upsert a SubActivity by (activity, order). Returns (sub, created)."""
        order = sub_data['order']
        matches = list(SubActivity.objects.filter(activity=activity, order=order).order_by('pk'))
        if matches:
            sub = matches[0]
            for extra in matches[1:]:
                extra.delete()
            if sync:
                for field, value in sub_data.items():
                    setattr(sub, field, value)
                sub.save()
            return sub, False
        return SubActivity.objects.create(activity=activity, **sub_data), True

    def _upsert_exercise(self, sub, order, ex_data, sync):
        """Upsert an Exercise by (sub_activity, order). Returns (exercise, created)."""
        defaults = {k: v for k, v in ex_data.items() if k != 'order'}
        matches = list(Exercise.objects.filter(sub_activity=sub, order=order).order_by('pk'))
        if matches:
            exercise = matches[0]
            for extra in matches[1:]:
                extra.delete()
            if sync:
                for field, value in defaults.items():
                    setattr(exercise, field, value)
                exercise.save()
            return exercise, False
        return Exercise.objects.create(sub_activity=sub, order=order, **defaults), True

    def _replace_questions(self, exercise, questions_data):
        """Questions carry no learner-facing foreign keys (results reference the
        Exercise, not the Question), so it is safe to rebuild them cleanly."""
        exercise.questions.all().delete()
        for q_idx, q in enumerate(questions_data, 1):
            Question.objects.create(
                exercise=exercise,
                order=q_idx,
                question_text=q.get('text', ''),
                option_a=q.get('a', ''),
                option_b=q.get('b', ''),
                option_c=q.get('c', ''),
                option_d=q.get('d', ''),
                correct_answer=q.get('correct', ''),
                explanation=q.get('explanation', ''),
                left_item=q.get('left', ''),
                right_item=q.get('right', ''),
            )

    def _replace_bingo(self, exercise, bingo_words):
        exercise.bingo_cards.all().delete()
        for word, definition in bingo_words:
            BingoCard.objects.create(
                exercise=exercise,
                word=word,
                definition=definition,
            )
