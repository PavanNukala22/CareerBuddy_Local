"""Predefined role and experience data for the manual Resume Builder.

Everything the landing-page Resume Builder shows for a role — description,
responsibilities, required skills, the role-specific form fields, the
experience-level suggestions, the editable professional-summary templates and
the typical career path — is defined here. Nothing is generated: the builder
only offers these predefined, editable suggestions, and the candidate decides
what applies to them.

Admins can override any built-in role, or add a new one, from the Django admin
(``ResumeRoleTemplate``); ``get_roles()`` merges those rows over the defaults.
Adding a role never requires a new form — the builder renders every role from
this same structure.
"""
from django.utils.text import slugify

LEVEL_KEYS = ('fresher', '1-3', '3-5', '5+')
LEVEL_LABELS = {
    'fresher': 'Fresher',
    '1-3': '1–3 Years',
    '3-5': '3–5 Years',
    '5+': '5+ Years',
}
CATEGORY_LABELS = {
    'it': 'IT Role',
    'tech': 'Non-IT · Technical',
    'nt': 'Non-IT · Non-Technical',
}

# Shared, role-independent suggestions per experience level. Shown next to the
# role's own suggestions; never pre-selected.
LEVEL_COMMON = {
    'fresher': {
        'soft_skills': ['Communication', 'Teamwork', 'Problem-solving', 'Time management',
                        'Willingness to learn', 'Attention to detail'],
        'achievements': [
            'Secured [rank / grade] in [exam, course or competition]',
            'Completed [project or training] with [result]',
            'Received [award or recognition] for [activity]',
        ],
        'emphasis': 'Focus on your education, academic projects, internships and training. '
                    'Tick only what you have actually studied or practised.',
    },
    '1-3': {
        'soft_skills': ['Team collaboration', 'Communication', 'Time management', 'Problem-solving',
                        'Customer orientation', 'Adaptability'],
        'achievements': [
            'Completed [task or project] [X days / weeks] ahead of schedule',
            'Reduced [errors / time / cost] by [X%] by [what you did]',
            'Recognised by [manager / client] for [contribution]',
        ],
        'emphasis': 'Describe the work you actually did, the tools you used and the results you contributed to.',
    },
    '3-5': {
        'soft_skills': ['Team coordination', 'Process improvement', 'Mentoring', 'Problem-solving',
                        'Cross-functional collaboration', 'Decision making'],
        'achievements': [
            'Owned [project / process] and delivered [result]',
            'Improved [process], resulting in [measurable outcome]',
            'Trained [number] team members on [skill or process]',
        ],
        'emphasis': 'Highlight the work you owned, the improvements you made and verified accomplishments.',
    },
    '5+': {
        'soft_skills': ['Stakeholder management', 'Team leadership', 'Process optimisation',
                        'Strategic thinking', 'Negotiation', 'Decision making'],
        'achievements': [
            'Led [team / project] of [size or value] to [result]',
            'Delivered [programme] within [budget / schedule]',
            'Optimised [process], saving [time / cost]',
        ],
        'emphasis': 'Add senior responsibilities only where they apply to you — leadership, budget or '
                    'strategy are never assumed from years of experience.',
    },
}

SUMMARY_PATTERNS = {
    'fresher': [
        'Motivated entry-level {title} candidate with an academic foundation in {focus}. Interested in '
        'applying {knowledge} knowledge, problem-solving and communication skills to support {goal}.',
        'Entry-level {title} candidate with [degree / qualification] and hands-on exposure to {focus} '
        'through [academic projects, internships or training]. Eager to contribute to {goal}.',
    ],
    '1-3': [
        '{title} with [X] years of experience in [industry or domain], specializing in [verified skills]. '
        'Experienced in [candidate-provided responsibilities or achievements].',
    ],
    '3-5': [
        '{title} with [X] years of experience in [industry or domain], specializing in [verified skills]. '
        'Experienced in [responsibilities you have owned], with verified results such as '
        '[measurable achievements].',
    ],
    '5+': [
        '{title} with [X] years of experience in [industry or domain] and specialization in '
        '[verified skills]. Experienced in [senior responsibilities you have actually held], with a '
        'record of [measurable achievements].',
    ],
}

DEFAULT_SECTIONS = {
    'fresher': ['Professional Summary', 'Core Skills', 'Education', 'Projects', 'Internships',
                'Professional Experience', 'Certifications & Training', 'Achievements',
                'Additional Information'],
    'experienced': ['Professional Summary', 'Core Skills', 'Professional Experience', 'Key Achievements',
                    'Projects', 'Internships', 'Education', 'Certifications & Training',
                    'Additional Information'],
}


def _split(value):
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value or '').split('|') if part.strip()]


def _level(skills, responsibilities, projects='', training=''):
    return {
        'skills': _split(skills),
        'responsibilities': _split(responsibilities),
        'projects': _split(projects),
        'training': _split(training),
    }


def _role(title, category, icon, industry, subtitle, description, responsibilities, required, path, *,
          fields, recommended, certifications, focus, knowledge, goal, fresher, early, mid, senior,
          experience_label='Professional Experience', slug=None):
    return {
        'slug': slug or slugify(title.replace('&', 'and').replace('/', ' ')),
        'title': title,
        'category': category,
        'icon': icon,
        'industry': industry,
        'subtitle': subtitle,
        'description': description,
        'responsibilities': _split(responsibilities),
        'required_skills': _split(required),
        'recommended_skills': _split(recommended),
        'career_path': _split(path),
        'certifications': _split(certifications),
        'fields': [
            {'key': slugify(label)[:40] or f'field-{i}', 'label': label, 'options': _split(options)}
            for i, (label, options) in enumerate(fields)
        ],
        'levels': {'fresher': fresher, '1-3': early, '3-5': mid, '5+': senior},
        'summary_focus': {'focus': focus, 'knowledge': knowledge, 'goal': goal},
        'experience_label': experience_label,
    }


IT = 'Information Technology'
PROJECTS = 'Engineering, Construction & Energy Projects'

BUILTIN_ROLES = [
    # ------------------------------------------------------------------ IT
    _role(
        'Software Developer', 'it', 'code', IT, 'Frontend, backend, full-stack',
        'Software Developers design, build and maintain the applications and websites people use every day. '
        'You turn requirements into clean, tested code and work closely with designers, testers and product teams.',
        'Write, review and debug clean, maintainable code|Build features, APIs and database integrations|'
        'Collaborate in agile teams and join code reviews|Fix bugs, improve performance and ship releases',
        'JavaScript|Python / Java|HTML & CSS|React / Node.js|SQL & Databases|Git & GitHub|REST APIs|Problem Solving',
        'Intern / Trainee|Junior Developer|Software Developer|Senior Developer|Tech Lead',
        fields=[
            ('Programming languages', 'JavaScript|Python|Java|C#|C++|TypeScript|Go|PHP'),
            ('Frontend technologies', 'HTML5|CSS3|Responsive design|Bootstrap|Tailwind CSS|Accessibility basics|JavaScript (ES6+)'),
            ('Backend technologies', 'Node.js|REST APIs|GraphQL|Authentication (JWT / OAuth)|Microservices|Server-side validation'),
            ('Databases', 'MySQL|PostgreSQL|MongoDB|SQL Server|Oracle|Redis'),
            ('Frameworks', 'React|Angular|Vue.js|Express.js|Django|Flask|Spring Boot|.NET Core|Laravel'),
            ('Tools & practices', 'Git & GitHub|Docker|Jira|Postman|Unit testing|Agile / Scrum|CI/CD basics'),
        ],
        recommended='TypeScript|Docker|Cloud Basics (AWS / Azure)|Unit Testing|Agile / Scrum|System Design',
        certifications='AWS Certified Developer – Associate|Oracle Certified Professional: Java SE|'
                       'Microsoft Certified: Azure Developer Associate|Meta Front-End Developer Certificate|'
                       'Scrum Fundamentals Certified',
        focus='programming fundamentals, web development and database concepts', knowledge='software development',
        goal='building reliable, well-tested applications',
        fresher=_level('Programming Fundamentals|Data Structures & Algorithms|HTML, CSS & JavaScript Basics|SQL Basics|Version Control with Git|Debugging Basics',
                       'Developed features for an academic or internship project under guidance|Wrote and debugged code following coding standards|Tested modules and fixed reported bugs|Documented code and project setup steps',
                       'Personal portfolio website (HTML, CSS, JavaScript)|Student management system with CRUD operations|REST API for a to-do or library application|E-commerce product catalogue with search and filters',
                       'Full-stack web development training|Data structures and algorithms course|Git and GitHub workshop|Software development internship'),
        early=_level('Feature Development|REST API Integration|Unit Testing|Code Reviews|Agile / Scrum|Debugging & Troubleshooting',
                     'Developed and maintained application features based on user stories|Integrated REST APIs and third-party services|Wrote unit tests and fixed defects reported by QA|Participated in code reviews, sprint planning and stand-ups'),
        mid=_level('System Design Basics|Performance Optimization|Code Quality & Refactoring|CI/CD Pipelines|Mentoring Junior Developers|Technical Documentation',
                   'Owned end-to-end delivery of modules from design to deployment|Improved application performance and response times|Refactored legacy code to improve maintainability|Reviewed code and guided junior developers on best practices'),
        senior=_level('Software Architecture|Scalability & Reliability|Technical Leadership|Cross-team Collaboration|Security Best Practices|Technical Roadmapping',
                      'Designed architecture for scalable services and applications|Led a development team or workstream through releases|Set coding standards, review processes and quality gates|Worked with product and business stakeholders on technical decisions'),
    ),
    _role(
        'Data Analyst', 'it', 'chart', IT, 'SQL, Excel, BI dashboards',
        'Data Analysts collect, clean and interpret data to help businesses make better decisions. You find '
        'patterns, build dashboards and turn numbers into clear stories for managers and clients.',
        'Query and clean data from multiple sources|Build dashboards and regular reports|'
        'Find trends and present insights to stakeholders|Maintain data accuracy and documentation',
        'SQL|Advanced Excel|Power BI / Tableau|Python (Pandas)|Statistics|Data Cleaning|Data Visualization|Communication',
        'Junior Analyst|Data Analyst|Senior Analyst|Analytics Manager|Head of Analytics',
        fields=[
            ('Data querying (SQL)', 'Joins & subqueries|Window functions|MySQL|PostgreSQL|SQL Server|BigQuery'),
            ('Spreadsheet analysis', 'Advanced Excel|Pivot tables|VLOOKUP / XLOOKUP|Power Query|Google Sheets|Data validation'),
            ('BI & visualization', 'Power BI|Tableau|Looker Studio|DAX|Dashboard design|Matplotlib / Seaborn'),
            ('Programming for analysis', 'Python|Pandas|NumPy|R|Jupyter Notebook'),
            ('Statistics & methods', 'Descriptive statistics|Hypothesis testing|Regression analysis|A/B testing|Forecasting basics'),
            ('Data quality', 'Data cleaning|Data validation|ETL basics|Data documentation'),
        ],
        recommended='Power Query|DAX|Python (Pandas)|Statistics|Storytelling with Data|Google Sheets',
        certifications='Google Data Analytics Professional Certificate|Microsoft Certified: Power BI Data Analyst Associate|'
                       'Tableau Desktop Specialist|IBM Data Analyst Professional Certificate',
        focus='data analysis, statistics and data visualization', knowledge='data analysis',
        goal='data-driven business decisions',
        fresher=_level('Excel Fundamentals|SQL Basics|Data Cleaning Basics|Descriptive Statistics|Dashboard Basics|Python for Data Analysis (Basics)',
                       'Cleaned and organised datasets for academic or internship analysis|Prepared charts and summary reports from raw data|Wrote basic SQL queries to extract required data|Presented findings to project guides or team members',
                       'Sales performance dashboard in Power BI or Tableau|Exploratory data analysis of a public dataset using Python|Customer churn analysis using Excel and SQL|Weather or public-health data trend analysis',
                       'Data analytics certification course|SQL for data analysis course|Power BI / Tableau training|Python for data science workshop'),
        early=_level('Report Automation|Advanced SQL|KPI Tracking|Data Visualization|Stakeholder Reporting|Power Query',
                     'Built and maintained recurring reports and dashboards|Wrote SQL queries to extract and combine data from multiple sources|Tracked business KPIs and flagged unusual trends|Supported teams with ad-hoc data requests and analysis'),
        mid=_level('Advanced Analytics|Data Modelling|Process Automation|Business Requirement Analysis|A/B Testing|Mentoring Analysts',
                   'Owned analytics for a business function or product area|Automated manual reports, saving recurring effort|Designed data models and KPI definitions with stakeholders|Delivered insights that informed business decisions'),
        senior=_level('Analytics Strategy|Data Governance|Team Leadership|Stakeholder Management|Forecasting & Planning|Analytics Roadmap',
                      'Defined analytics priorities and reporting standards|Led a team of analysts or an analytics workstream|Partnered with leadership on metrics and business planning|Established data quality and governance practices'),
    ),
    _role(
        'AI / ML Engineer', 'it', 'brain', IT, 'Models, NLP, automation',
        'AI / ML Engineers build systems that learn from data, from recommendation engines to chatbots and vision '
        'tools. You train, evaluate and deploy models that solve real business problems.',
        'Prepare datasets and engineer features|Train, tune and evaluate machine learning models|'
        'Deploy models into production applications|Monitor model performance and retrain when needed',
        'Python|Machine Learning|Deep Learning|TensorFlow / PyTorch|NLP|Statistics & Maths|SQL|Model Deployment',
        'ML Intern|Junior ML Engineer|ML Engineer|Senior ML Engineer|AI Architect',
        fields=[
            ('Programming', 'Python|SQL|R|Java|Bash'),
            ('Machine learning techniques', 'Supervised learning|Unsupervised learning|Feature engineering|Model evaluation|Hyperparameter tuning|Ensemble methods'),
            ('Deep learning & NLP', 'Neural networks|CNNs|RNNs / LSTMs|Transformers|NLP preprocessing|Computer vision'),
            ('Frameworks & libraries', 'scikit-learn|TensorFlow|PyTorch|Keras|Pandas|NumPy|Hugging Face'),
            ('Deployment & MLOps', 'Flask / FastAPI|Docker|MLflow|Model monitoring|Cloud ML (AWS / GCP / Azure)'),
            ('Maths & statistics', 'Linear algebra|Probability|Statistics|Optimization'),
        ],
        recommended='MLOps|Docker|Cloud ML Services|Hugging Face|Data Visualization|Git',
        certifications='TensorFlow Developer Certificate|AWS Certified Machine Learning – Specialty|'
                       'Google Professional Machine Learning Engineer|Microsoft Certified: Azure AI Engineer Associate|'
                       'DeepLearning.AI Specialization',
        focus='machine learning, Python programming and data analysis', knowledge='machine learning',
        goal='practical, data-driven AI solutions',
        fresher=_level('Python Programming|Machine Learning Fundamentals|Data Preprocessing|scikit-learn Basics|Statistics & Probability|Model Evaluation Basics',
                       'Prepared and cleaned datasets for academic or internship ML projects|Trained and compared baseline machine learning models|Evaluated models using appropriate metrics|Documented experiments and results',
                       'Image classification model using CNNs|Sentiment analysis on product reviews|House price prediction using regression|Movie or product recommendation system',
                       'Machine learning specialization course|Deep learning course|Kaggle competitions or practice notebooks|AI / ML internship or training'),
        early=_level('Feature Engineering|Model Training & Tuning|Deep Learning Frameworks|Model Deployment Basics|Experiment Tracking|SQL for ML',
                     'Built and trained ML models for defined business use cases|Engineered features and improved model accuracy|Deployed models as APIs with support from the team|Monitored model outputs and reported issues'),
        mid=_level('MLOps|NLP / Computer Vision|Model Optimization|Data Pipelines|Production ML Systems|Mentoring',
                   'Owned ML models from data preparation to production deployment|Built reusable training and data pipelines|Optimised model latency, accuracy or cost|Collaborated with engineering and product teams on ML features'),
        senior=_level('ML System Architecture|Responsible AI Practices|Team Leadership|Research to Production|Stakeholder Management|Technical Strategy',
                      'Designed architecture for production machine learning systems|Led ML projects or a team of engineers|Set evaluation, monitoring and responsible-AI standards|Advised stakeholders on feasible ML use cases'),
    ),
    _role(
        'Cloud & DevOps', 'it', 'layers', IT, 'AWS, Azure, CI/CD',
        'Cloud & DevOps Engineers keep applications running smoothly in the cloud. You automate builds and '
        'deployments, manage infrastructure as code and make releases fast and reliable.',
        'Design and manage cloud infrastructure|Build CI/CD pipelines for automated releases|'
        'Monitor systems, logs and costs|Improve reliability, security and scalability',
        'AWS / Azure|Linux|Docker|Kubernetes|CI/CD (Jenkins, GitHub Actions)|Terraform|Scripting (Bash/Python)|Monitoring',
        'Junior DevOps|DevOps Engineer|Senior DevOps|Cloud Architect|Platform Lead',
        fields=[
            ('Cloud platforms', 'AWS|Microsoft Azure|Google Cloud|EC2 / Virtual machines|S3 / Blob storage|IAM|VPC / Networking'),
            ('Containers & orchestration', 'Docker|Kubernetes|Helm|Amazon ECS / EKS|Azure AKS'),
            ('CI/CD', 'Jenkins|GitHub Actions|GitLab CI|Azure DevOps|Argo CD'),
            ('Infrastructure as code', 'Terraform|Ansible|CloudFormation|ARM / Bicep'),
            ('Monitoring & logging', 'Prometheus|Grafana|CloudWatch|ELK Stack|Datadog'),
            ('Scripting & OS', 'Linux administration|Bash|Python|PowerShell|Networking basics'),
        ],
        recommended='Kubernetes|Terraform|Python Scripting|Prometheus / Grafana|Security Basics|Ansible',
        certifications='AWS Certified Solutions Architect – Associate|AWS Certified Cloud Practitioner|'
                       'Microsoft Certified: Azure Administrator Associate|Certified Kubernetes Administrator (CKA)|'
                       'HashiCorp Certified: Terraform Associate',
        focus='Linux, cloud fundamentals and automation', knowledge='cloud and DevOps',
        goal='reliable, automated software delivery',
        fresher=_level('Linux Fundamentals|Cloud Basics (AWS / Azure)|Git & Version Control|Docker Basics|Shell Scripting Basics|Networking Basics',
                       'Set up virtual machines and services in a lab or internship environment|Wrote basic shell scripts to automate routine tasks|Built a simple CI pipeline for a sample project|Documented setup and deployment steps',
                       'CI/CD pipeline for a sample web app using GitHub Actions|Containerised application deployed with Docker Compose|Static website hosted on AWS S3 with CloudFront|Infrastructure provisioning with Terraform (lab)',
                       'AWS Cloud Practitioner preparation course|Docker and Kubernetes training|Linux administration course|DevOps bootcamp or internship'),
        early=_level('CI/CD Pipeline Maintenance|Container Deployment|Cloud Resource Management|Monitoring & Alerts|Infrastructure as Code|Incident Support',
                     'Maintained CI/CD pipelines for application releases|Deployed and managed containerised applications|Managed cloud resources, access and backups|Responded to alerts and supported incident resolution'),
        mid=_level('Kubernetes Operations|Cloud Cost Optimization|Security & Compliance|Release Automation|Reliability Engineering|Mentoring',
                   'Owned deployment pipelines and release processes for services|Automated infrastructure provisioning with IaC|Improved system reliability, monitoring and alerting|Reduced cloud costs through right-sizing and cleanup'),
        senior=_level('Cloud Architecture|Platform Engineering|DevSecOps|Disaster Recovery Planning|Team Leadership|Stakeholder Management',
                      'Designed cloud architecture for scalable, secure workloads|Led platform or DevOps initiatives across teams|Defined DevSecOps, backup and disaster recovery standards|Worked with engineering leadership on the infrastructure roadmap'),
    ),
    _role(
        'QA / Test Engineer', 'it', 'bug', IT, 'Manual and automation testing',
        'QA / Test Engineers make sure software works before users see it. You plan tests, find defects early and '
        'automate checks so every release is dependable.',
        'Write test plans, cases and scenarios|Run manual and automated tests|Log, track and retest defects|'
        'Work with developers to improve quality',
        'Manual Testing|Test Case Design|Selenium / Playwright|API Testing (Postman)|SQL Basics|Bug Tracking (Jira)|SDLC & Agile|Attention to Detail',
        'QA Trainee|Test Engineer|Senior QA|Automation Lead|QA Manager',
        fields=[
            ('Manual testing', 'Functional testing|Regression testing|Smoke & sanity testing|Exploratory testing|UAT support|Cross-browser testing'),
            ('Test design & documentation', 'Test plans|Test cases|Test scenarios|Traceability matrix|Bug reports'),
            ('Test automation', 'Selenium WebDriver|Playwright|Cypress|TestNG / JUnit|PyTest|Page Object Model'),
            ('API & database testing', 'Postman|REST Assured|SQL queries|API test automation'),
            ('Tools & process', 'Jira|TestRail|Git|Jenkins|Agile / Scrum|STLC / SDLC'),
            ('Performance & other testing', 'JMeter|Mobile testing|Accessibility testing|Security testing basics'),
        ],
        recommended='Playwright|Postman|JMeter|CI/CD Basics|Mobile Testing|SQL',
        certifications='ISTQB Certified Tester Foundation Level (CTFL)|ISTQB Advanced Level Test Automation Engineer|'
                       'Certified Agile Tester|Selenium WebDriver Certification',
        focus='software testing concepts, test case design and defect tracking', knowledge='software testing',
        goal='high-quality, reliable software releases',
        fresher=_level('Manual Testing Fundamentals|Test Case Writing|SDLC & STLC|Bug Reporting|SQL Basics|Selenium Basics',
                       'Executed test cases for academic or internship projects|Logged defects with clear steps to reproduce|Prepared test scenarios from requirements|Retested fixes and updated test status',
                       'Test plan and test cases for an e-commerce website|Selenium automation suite for a demo web application|API testing collection for a public REST API using Postman|Bug report and regression checklist for a mobile app',
                       'ISTQB Foundation preparation course|Selenium with Java / Python training|API testing with Postman course|QA internship or training'),
        early=_level('Test Automation|API Testing|Regression Suite Maintenance|Defect Lifecycle Management|Agile Testing|Cross-browser Testing',
                     'Designed and executed functional and regression test cases|Automated test scenarios using Selenium or similar tools|Tested APIs and validated data in databases|Worked with developers to reproduce and close defects'),
        mid=_level('Automation Framework Design|CI Integration of Tests|Performance Testing|Test Strategy|Mentoring Testers|Quality Metrics',
                   'Owned testing for releases or product modules|Built and maintained automation frameworks|Integrated automated tests into CI/CD pipelines|Defined test coverage and quality metrics'),
        senior=_level('QA Strategy|Test Process Improvement|Team Leadership|Release Quality Governance|Stakeholder Management|Tool Evaluation',
                      'Defined QA strategy and standards for products or programmes|Led a team of manual and automation testers|Introduced process improvements that strengthened release quality|Reported quality status to delivery and business stakeholders'),
    ),
    _role(
        'Web Designer', 'it', 'globe', IT, 'UI/UX and web experiences',
        'Web Designers shape how websites and apps look and feel. You create layouts, visuals and prototypes that '
        'are attractive, easy to use and work well on every screen size.',
        'Design wireframes, mockups and prototypes|Build responsive pages with HTML and CSS|'
        'Maintain brand consistency across pages|Gather feedback and improve usability',
        'Figma / Adobe XD|HTML & CSS|Responsive Design|UI/UX Principles|Typography & Colour|JavaScript Basics|Wireframing|Creativity',
        'Junior Designer|Web Designer|UI/UX Designer|Senior Designer|Design Lead',
        fields=[
            ('Design tools', 'Figma|Adobe XD|Photoshop|Illustrator|Canva|Sketch'),
            ('UI/UX practice', 'Wireframing|Prototyping|User research basics|Usability testing|Information architecture|Design systems'),
            ('Front-end build', 'HTML5|CSS3|Flexbox & Grid|JavaScript basics|Bootstrap|Tailwind CSS'),
            ('Visual design', 'Typography|Colour theory|Layout & grids|Iconography|Brand guidelines'),
            ('Web platforms', 'WordPress|Webflow|Shopify|Wix|SEO basics'),
            ('Accessibility & responsive design', 'Responsive design|Mobile-first design|WCAG basics|Cross-browser checks'),
        ],
        recommended='Design Systems|Usability Testing|WordPress|Accessibility (WCAG)|Motion Design Basics|SEO Basics',
        certifications='Google UX Design Professional Certificate|Adobe Certified Professional|'
                       'Interaction Design Foundation Certificate|Figma Professional Certificate',
        focus='visual design, UI/UX principles and responsive web layouts', knowledge='web and UI design',
        goal='clear, accessible and engaging digital experiences',
        fresher=_level('Figma Basics|HTML & CSS|Wireframing|Typography & Colour|Responsive Design Basics|Canva',
                       'Created wireframes and mockups for academic or internship projects|Built responsive pages using HTML and CSS|Prepared social media or marketing graphics|Incorporated feedback from mentors or users into designs',
                       'Personal portfolio website design and build|Mobile app UI redesign case study in Figma|Landing page for a local business|Design system with reusable UI components',
                       'UI/UX design course|Figma training|Front-end web development course|Graphic design workshop'),
        early=_level('UI Design|Prototyping|Design Handoff|Responsive Layouts|Brand Consistency|Usability Testing',
                     'Designed UI screens and interactive prototypes for websites or apps|Built responsive web pages and landing pages|Worked with developers on design handoff and implementation|Maintained brand consistency across digital assets'),
        mid=_level('Design Systems|UX Research|Conversion Optimization|Accessibility (WCAG)|Stakeholder Presentations|Mentoring Designers',
                   'Owned design for product features or client websites end to end|Created and maintained a design system or component library|Ran usability tests and improved user flows|Presented design decisions to clients or stakeholders'),
        senior=_level('Design Leadership|UX Strategy|Design Operations|Cross-functional Collaboration|Client Management|Creative Direction',
                      'Led design direction for products, brands or client accounts|Managed and mentored a team of designers|Defined UX standards and design review processes|Partnered with product and business leaders on user experience strategy'),
    ),
    _role(
        'Systems Admin', 'it', 'net', IT, 'Networks and infrastructure',
        'Systems Administrators keep an organisation’s servers, networks and devices healthy. You handle setup, '
        'updates, backups and user support so teams can work without interruption.',
        'Install, configure and update servers and systems|Manage user accounts, access and backups|'
        'Monitor networks and resolve incidents|Document procedures and support users',
        'Windows / Linux Server|Networking (TCP/IP, DNS)|Active Directory|Virtualization|Backup & Recovery|Shell Scripting|Troubleshooting|Customer Support',
        'Support Engineer|Systems Admin|Senior Sysadmin|Infrastructure Lead|IT Manager',
        fields=[
            ('Operating systems', 'Windows Server|Linux (RHEL / Ubuntu)|macOS support|Patch management'),
            ('Networking', 'TCP/IP|DNS|DHCP|VLANs|VPN|Firewalls'),
            ('Directory & identity', 'Active Directory|Group Policy|Microsoft Entra ID (Azure AD)|Microsoft 365 administration'),
            ('Virtualization & cloud', 'VMware|Hyper-V|Azure|AWS'),
            ('Backup & monitoring', 'Backup & recovery|Nagios / Zabbix|Veeam|Disaster recovery'),
            ('Scripting & support', 'PowerShell|Bash|Ticketing (ServiceNow / Jira)|Hardware troubleshooting'),
        ],
        recommended='PowerShell|Cloud Administration|ITIL Basics|Security Hardening|VMware|Monitoring Tools',
        certifications='CompTIA A+|CompTIA Network+|Cisco Certified Network Associate (CCNA)|'
                       'Microsoft Certified: Azure Administrator Associate|Red Hat Certified System Administrator (RHCSA)',
        focus='operating systems, networking fundamentals and IT support', knowledge='system administration',
        goal='stable and secure IT operations',
        fresher=_level('Windows & Linux Basics|Networking Fundamentals|Hardware & Software Troubleshooting|Active Directory Basics|Customer Support|Documentation',
                       'Installed and configured operating systems and software in labs or internships|Assisted users with hardware and software issues|Configured basic network settings and user accounts|Documented troubleshooting steps and resolutions',
                       'Home lab with Windows Server and Active Directory|Small office network design with VLANs|Automated backup script using PowerShell or Bash|Linux web server setup and hardening',
                       'CompTIA A+ / Network+ preparation|CCNA training|Microsoft Windows Server course|IT support internship'),
        early=_level('Server Administration|User & Access Management|Patch Management|Backup Operations|Incident & Ticket Handling|Network Troubleshooting',
                     'Administered Windows and Linux servers and user accounts|Applied patches and maintained system updates|Monitored backups and resolved incidents through the ticketing system|Supported users with network, email and device issues'),
        mid=_level('Virtualization|Automation with Scripts|Infrastructure Monitoring|Security Hardening|Vendor Coordination|Mentoring Support Staff',
                   'Owned server, virtualization and backup infrastructure|Automated routine administration tasks with scripts|Improved monitoring and reduced recurring incidents|Coordinated with vendors for hardware, licences and support'),
        senior=_level('Infrastructure Planning|IT Service Management|Disaster Recovery|Team Leadership|Budget & Vendor Management|Security & Compliance',
                      'Planned infrastructure upgrades and capacity|Led IT support or infrastructure teams|Defined backup, disaster recovery and access policies|Managed IT vendors, licences and infrastructure budgets'),
    ),
    _role(
        'Cyber Security', 'it', 'shield', IT, 'Protect systems and data',
        'Cyber Security professionals defend systems, networks and data from attacks. You find weak points, monitor '
        'threats and respond quickly when something goes wrong.',
        'Monitor systems for threats and suspicious activity|Run vulnerability scans and security audits|'
        'Respond to and document security incidents|Apply security policies and awareness training',
        'Network Security|Ethical Hacking|SIEM Tools|Vulnerability Assessment|Linux|Cryptography Basics|Incident Response|Risk Management',
        'SOC Analyst|Security Analyst|Security Engineer|Security Architect|CISO',
        fields=[
            ('Security operations', 'SIEM monitoring|Log analysis|Alert triage|Threat intelligence|Incident response'),
            ('Security tools', 'Splunk|IBM QRadar|Wireshark|Nmap|Burp Suite|Metasploit|Nessus'),
            ('Network & system security', 'Firewalls|IDS / IPS|Endpoint security|System hardening|VPN'),
            ('Vulnerability management', 'Vulnerability scanning|Penetration testing|OWASP Top 10|Patch tracking'),
            ('Governance & compliance', 'ISO 27001|NIST CSF|Risk assessment|Security policies|Security awareness'),
            ('Platforms & scripting', 'Linux|Windows security|Python|Bash|Cloud security basics'),
        ],
        recommended='Cloud Security|Python Scripting|Threat Hunting|ISO 27001|Penetration Testing|Digital Forensics Basics',
        certifications='CompTIA Security+|Certified Ethical Hacker (CEH)|Cisco CyberOps Associate|'
                       'ISC2 Certified in Cybersecurity (CC)|CISSP|OSCP',
        focus='network security, threat analysis and security tools', knowledge='cyber security',
        goal='protecting systems and data',
        fresher=_level('Networking Fundamentals|Security Concepts (CIA Triad)|Linux Basics|Wireshark Basics|OWASP Top 10|Log Analysis Basics',
                       'Analysed logs and network traffic in lab or internship environments|Performed vulnerability scans on practice systems|Documented findings and remediation steps|Followed security policies and incident procedures',
                       'Home SOC lab with a SIEM and log sources|Vulnerability assessment of a deliberately vulnerable web app (DVWA)|Network traffic analysis with Wireshark|Phishing awareness campaign material',
                       'CompTIA Security+ preparation|Ethical hacking course|SOC analyst training|Capture the Flag (CTF) practice'),
        early=_level('SIEM Monitoring|Incident Triage|Vulnerability Assessment|Endpoint Security|Security Reporting|Threat Analysis',
                     'Monitored SIEM alerts and triaged security events|Ran vulnerability scans and tracked remediation|Supported incident investigation and documentation|Prepared security reports for the team'),
        mid=_level('Penetration Testing|Incident Response|Cloud Security|Security Architecture Review|Threat Hunting|Mentoring Analysts',
                   'Owned incident response for security events|Conducted penetration tests and security reviews|Improved detection rules and monitoring coverage|Guided junior analysts and reviewed their findings'),
        senior=_level('Security Strategy|Risk Management|Governance & Compliance|Security Programme Leadership|Stakeholder Management|Security Architecture',
                      'Defined security policies, standards and roadmaps|Led a security operations or engineering team|Managed security risk, audits and compliance programmes|Advised leadership on security investments and risk'),
    ),

    # ------------------------------------------------------- NON-IT TECHNICAL
    _role(
        'Project Manager', 'tech', 'flag', PROJECTS, 'Plan, lead and deliver projects',
        'Project Managers own a project from kickoff to handover. You plan scope, schedule and budget, lead the site '
        'and office teams, and keep clients informed so work finishes safely, on time and within cost.',
        'Prepare project plans, schedules and budgets|Lead teams, contractors and vendors|'
        'Track progress, cost and risks weekly|Report to clients and senior management',
        'Project Planning|MS Project / Primavera|Budgeting & Cost Control|Risk Management|Contract Management|Stakeholder Communication|Team Leadership|Quality & Safety Standards',
        'Project Engineer|Senior Engineer|Project Manager|Senior Project Manager|Project Director',
        fields=[
            ('Project planning', 'Scope definition|Work breakdown structure (WBS)|Scheduling|Resource planning|Milestone tracking|Progress reporting'),
            ('MS Project / Primavera', 'MS Project|Primavera P6|Gantt charts|Critical path method (CPM)|Baseline & schedule updates|Earned value basics'),
            ('Budgeting and cost control', 'Budget preparation|Cost tracking|Cash flow monitoring|Variance analysis|Change order control'),
            ('Risk management', 'Risk identification|Risk register|Mitigation planning|Issue tracking'),
            ('Team leadership', 'Team coordination|Contractor management|Task delegation|Conflict resolution'),
            ('Stakeholder communication', 'Client reporting|Progress meetings|Minutes of meetings|Stakeholder updates|Presentations'),
        ],
        recommended='Earned Value Management|Contract Administration|Quality Management|HSE Awareness|Advanced Excel|Claims Management',
        certifications='Project Management Professional (PMP)|Certified Associate in Project Management (CAPM)|'
                       'PRINCE2 Foundation / Practitioner|Primavera P6 Certification|PMI Risk Management Professional (PMI-RMP)',
        focus='project planning, scheduling and team coordination', knowledge='project management',
        goal='successful project delivery',
        fresher=_level('Project Planning Fundamentals|MS Project Basics|Task Coordination|Risk Identification|Teamwork|Communication',
                       'Assisted in preparing project schedules and trackers|Coordinated tasks and follow-ups within a project team|Prepared minutes of meetings and progress notes|Helped identify and record project risks and issues',
                       'Project plan and schedule for a building or infrastructure project (academic)|Cost estimate and budget for a small construction project|Risk register for a sample industrial project|College event or project managed from planning to closure',
                       'Project management fundamentals course|MS Project or Primavera P6 training|CAPM preparation course|Site or industrial training'),
        early=_level('Project Scheduling|Progress Monitoring|Cost Tracking|Site Coordination|Documentation & Reporting|Contractor Coordination',
                     'Prepared and updated project schedules in MS Project or Primavera|Monitored progress and reported variances to the project manager|Tracked costs, quantities and change requests|Coordinated with site teams, vendors and clients'),
        mid=_level('Project Execution Management|Budget Control|Risk Management|Contract Administration|Team Coordination|Process Improvement',
                   'Managed execution of assigned projects or work packages|Controlled budgets, cash flow and change orders|Maintained risk registers and mitigation actions|Led coordination meetings with contractors and clients'),
        senior=_level('Project Delivery Ownership|Stakeholder Management|Commercial & Contract Management|Team Leadership|Portfolio Planning|Governance & Reporting',
                      'Owned delivery of projects for scope, schedule, cost and quality|Led multidisciplinary teams and subcontractors|Managed client relationships, claims and contract issues|Reported project performance to senior management'),
    ),
    _role(
        'Project Engineer', 'tech', 'gear', PROJECTS, 'Technical delivery and execution',
        'Project Engineers handle the technical side of a project. You review drawings, coordinate with site teams, '
        'monitor quality and make sure work follows specifications and schedule.',
        'Review drawings, specifications and BOQs|Coordinate between design, site and procurement|'
        'Monitor quality, progress and material use|Prepare technical reports and as-built records',
        'Engineering Drawings|AutoCAD|MS Project / Primavera|BOQ & Quantity Take-off|Quality Control|Technical Reporting|Coordination|Site Safety',
        'Graduate Engineer|Project Engineer|Senior Project Engineer|Project Manager|Project Director',
        fields=[
            ('Engineering drawings', 'Drawing review|Shop drawings|As-built drawings|P&IDs|GA drawings'),
            ('Design & drafting tools', 'AutoCAD|Revit|Navisworks|SolidWorks|STAAD Pro'),
            ('Planning & scheduling', 'MS Project|Primavera P6|Look-ahead schedules|Progress tracking'),
            ('Quantities & BOQ', 'BOQ review|Quantity take-off|Material reconciliation|Measurement sheets'),
            ('Quality control', 'Inspection & test plans (ITPs)|Material inspection|Method statements|NCR handling|QA/QC documentation'),
            ('Coordination & reporting', 'Technical reports|RFIs|Submittals|Vendor coordination|Site coordination'),
        ],
        recommended='Revit / BIM|Primavera P6|Commissioning|Contract Basics|HSE Awareness|Value Engineering',
        certifications='Primavera P6 Certification|AutoCAD Certified User / Professional|PMP or CAPM|NEBOSH IGC|Six Sigma Green Belt',
        focus='engineering drawings, project coordination and quality control', knowledge='engineering',
        goal='safe, on-schedule project execution',
        fresher=_level('Engineering Drawing Reading|AutoCAD Basics|MS Excel|Quantity Take-off Basics|Technical Documentation|Teamwork',
                       'Reviewed drawings and specifications during academic or industrial training|Assisted in quantity calculations and BOQ preparation|Supported site inspections and progress recording|Prepared technical notes and reports',
                       'Design and drawings for a small residential or industrial structure|Quantity take-off and BOQ for a sample project|Material selection study for a mechanical or electrical system|Final-year engineering design project',
                       'AutoCAD / Revit training|Primavera P6 or MS Project course|Industrial or site internship|QA/QC fundamentals course'),
        early=_level('Drawing Review|Material Submittals|Site Coordination|Progress Reporting|Quality Inspections|RFI Management',
                     'Reviewed drawings, specifications and BOQs for assigned work|Prepared material submittals and RFIs|Coordinated between design, site and procurement teams|Prepared progress and inspection reports'),
        mid=_level('Package Management|Technical Problem Solving|Subcontractor Coordination|Change Management|Quality Assurance|Mentoring Engineers',
                   'Managed technical delivery of assigned work packages|Resolved design and site issues with consultants|Coordinated subcontractors and material deliveries|Tracked variations and supported change orders'),
        senior=_level('Engineering Management|Technical Leadership|Client & Consultant Liaison|Cost & Schedule Control|Team Leadership|Commissioning & Handover',
                      'Led engineering teams across disciplines or packages|Represented the project in technical discussions with clients and consultants|Controlled cost and schedule for engineering deliverables|Managed testing, commissioning and handover documentation'),
    ),
    _role(
        'Site Engineer', 'tech', 'hat', PROJECTS, 'On-site execution and supervision',
        'Site Engineers supervise day-to-day work on the construction or plant site. You turn drawings into finished '
        'work, manage crews and materials, and keep quality and safety on track.',
        'Supervise site activities and workforce|Set out work from drawings and check dimensions|'
        'Maintain daily progress and material records|Enforce HSE rules and quality checks',
        'Site Supervision|Reading Drawings|Surveying / Total Station|AutoCAD|Quality Inspection|HSE Compliance|Material Management|Measurement & Billing',
        'Trainee Engineer|Site Engineer|Senior Site Engineer|Construction Manager|Project Manager',
        fields=[
            ('Site supervision', 'Workforce supervision|Daily progress monitoring|Method statement implementation|Subcontractor supervision|Work sequencing'),
            ('Drawings & setting out', 'Reading drawings|Setting out|Levelling|Total station|Auto level'),
            ('Quality inspection', 'Concrete works inspection|Reinforcement checks|Formwork checks|Material testing|Checklists & ITPs'),
            ('Measurement & billing', 'Measurement sheets|Running bills|Quantity verification|Material reconciliation'),
            ('HSE compliance', 'Toolbox talks|PPE compliance|Permit-to-work|Housekeeping|Safe work practices'),
            ('Tools & reporting', 'AutoCAD|MS Excel|Daily progress reports|Site diary'),
        ],
        recommended='Primavera P6|Revit / BIM Basics|Formwork Systems|Waterproofing|MEP Coordination|Quality Management',
        certifications='NEBOSH IGC|OSHA 30-Hour Construction|AutoCAD Certification|Primavera P6 Certification|Total Station / Surveying Certification',
        focus='site supervision, construction drawings and quality checks', knowledge='site engineering',
        goal='safe, high-quality execution on site',
        fresher=_level('Reading Construction Drawings|Basic Surveying|AutoCAD Basics|Quantity Calculation|Site Safety Awareness|Teamwork',
                       'Assisted site supervision during an internship or site training|Helped with setting out and levelling under supervision|Recorded daily progress and material usage|Followed safety rules and PPE requirements on site',
                       'Survey and levelling exercise (academic)|Design of a residential building with drawings|Concrete mix design and testing project|Estimation of materials for a small structure',
                       'Site internship or industrial training|Total station and surveying training|AutoCAD training|Construction safety awareness course'),
        early=_level('Site Execution|Setting Out|Quality Checks|Daily Progress Reporting|Labour & Material Management|Measurement & Billing',
                     'Supervised daily site activities and workforce|Set out work from drawings and checked levels and dimensions|Conducted quality checks for concrete, reinforcement and finishes|Maintained daily progress reports and measurement records'),
        mid=_level('Section or Area Management|Subcontractor Coordination|Quality Assurance|Planning & Scheduling|Cost Control on Site|Mentoring Junior Engineers',
                   'Managed an area or section of the site including subcontractors|Planned weekly work and look-ahead schedules|Resolved site issues with consultants and design teams|Verified subcontractor bills and quantities'),
        senior=_level('Construction Management|Site Leadership|Client & Consultant Coordination|Safety Leadership|Schedule & Cost Control|Handover Management',
                      'Led site teams across multiple work fronts|Coordinated with clients and consultants on progress and approvals|Drove safety and quality standards on site|Managed snagging, testing and handover'),
        experience_label='Site Experience',
    ),
    _role(
        'Estimation Engineer', 'tech', 'calc', PROJECTS, 'Costing, tendering and BOQs',
        'Estimation Engineers work out what a project will cost before it is won. You study tender documents, '
        'measure quantities, collect vendor rates and prepare competitive, accurate bids.',
        'Study tender drawings and specifications|Prepare quantity take-offs and BOQs|'
        'Collect vendor quotes and price the work|Compile tender submissions and cost reports',
        'Quantity Take-off|BOQ Preparation|Cost Estimation|Advanced Excel|AutoCAD|Tender Documentation|Rate Analysis|Negotiation',
        'Junior Estimator|Estimation Engineer|Senior Estimator|Chief Estimator|Commercial Manager',
        fields=[
            ('Quantity take-off', 'Manual take-off|Digital take-off (PlanSwift / Bluebeam)|Measurement standards (SMM / POMI)|Quantity verification'),
            ('BOQ preparation', 'BOQ preparation|BOQ pricing|Item descriptions|Provisional sums'),
            ('Cost estimation', 'Rate analysis|Material costing|Labour productivity|Plant & equipment costs|Overheads & profit'),
            ('Tendering', 'Tender document review|Pre-bid queries|Technical & commercial bids|Bid submissions|Clarifications'),
            ('Vendor & market rates', 'Vendor quotations|Quote comparison|Market rate research|Negotiation'),
            ('Estimation tools', 'Advanced Excel|AutoCAD|CostX|Candy|MS Project'),
        ],
        recommended='CostX / Candy|Contract Conditions (FIDIC)|Value Engineering|Cash Flow Forecasting|Negotiation|Planning Basics',
        certifications='RICS APC (in progress or completed)|CostX Certification|Certified Cost Professional (CCP)|'
                       'Advanced Excel Certification|Primavera P6 Certification',
        focus='quantity surveying, cost estimation and tender documentation', knowledge='cost estimation',
        goal='accurate, competitive project pricing',
        fresher=_level('Quantity Take-off Basics|MS Excel|AutoCAD Basics|Rate Analysis Basics|Reading Drawings|Attention to Detail',
                       'Prepared quantity take-offs from drawings during academic or internship work|Assisted in preparing BOQs and rate analysis|Collected and compared material rates|Checked calculations for accuracy',
                       'Detailed estimate and BOQ for a residential building|Rate analysis for concrete and masonry works|Cost comparison of construction methods|Tender document study for a public works project',
                       'Quantity surveying course|Estimation and costing training|Advanced Excel course|CostX or PlanSwift training'),
        early=_level('BOQ Preparation|Rate Analysis|Vendor Quotation Comparison|Tender Support|Cost Reporting|Variation Estimation',
                     'Prepared quantity take-offs and BOQs for tenders|Performed rate analysis and priced BOQ items|Collected and compared vendor quotations|Supported preparation of tender submissions'),
        mid=_level('Tender Management|Cost Planning|Value Engineering|Commercial Negotiation|Risk Pricing|Mentoring Estimators',
                   'Led estimates for tenders of defined packages or projects|Prepared cost plans and value engineering options|Priced risks, overheads and contingencies|Negotiated rates with suppliers and subcontractors'),
        senior=_level('Estimation Department Leadership|Bid Strategy|Commercial Management|Contract Review|Cost Database Management|Stakeholder Management',
                      'Led the estimation team and tender pipeline|Defined bid strategy and pricing with management|Reviewed contract terms and commercial risks|Maintained cost databases and estimation standards'),
    ),
    _role(
        'Back Office Manager', 'tech', 'clip', PROJECTS, 'Project documentation and support',
        'Back Office Managers keep the project’s paperwork and commercial side in order. You lead the team that '
        'handles documents, billing, procurement support and reporting for site and management.',
        'Lead the back-office team and daily workflow|Manage project documents, billing and records|'
        'Coordinate with site, accounts and purchase|Prepare MIS and management reports',
        'Document Control|MIS Reporting|Advanced Excel|Billing & Invoicing|ERP / SAP|Team Management|Vendor Coordination|Communication',
        'Back Office Executive|Senior Executive|Back Office Manager|Operations Manager|Head of Operations',
        fields=[
            ('Document control', 'Document register|Transmittals|Version control|Archiving|EDMS (Aconex / SharePoint)'),
            ('Billing & invoicing', 'Client billing|Subcontractor bills|Invoice tracking|Payment follow-up'),
            ('MIS & reporting', 'MIS reports|Advanced Excel|Dashboards|Progress reports'),
            ('ERP & systems', 'SAP|Oracle|Tally|ERP data entry'),
            ('Team management', 'Work allocation|Performance tracking|Staff training|Process documentation'),
            ('Coordination', 'Vendor coordination|Site coordination|Accounts coordination|Purchase coordination'),
        ],
        recommended='Power BI|SAP|Aconex / EDMS|Contract Documentation|Process Mapping|Team Management',
        certifications='Advanced Excel Certification|SAP End User Certification|Document Control Certification|Lean Six Sigma Yellow Belt',
        focus='documentation, MIS reporting and project support', knowledge='back-office operations',
        goal='accurate project documentation and reporting',
        fresher=_level('MS Excel|Document Management Basics|Data Entry Accuracy|Email Communication|ERP Basics|Time Management',
                       'Maintained documents and records during internships or training|Prepared simple reports in Excel|Supported billing and documentation tasks|Coordinated emails and follow-ups with teams',
                       'Document control register for a sample project|MIS dashboard in Excel|Process flow documentation for an office function',
                       'Advanced Excel course|ERP / SAP basics training|Document control training|Office administration course'),
        early=_level('Document Control|Billing Support|MIS Reporting|ERP Data Management|Vendor Follow-up|Records Management',
                     'Maintained project documents, registers and transmittals|Prepared MIS reports for site and management|Processed bills and tracked invoice status|Coordinated with site, accounts and purchase teams'),
        mid=_level('Team Supervision|Process Improvement|Billing Control|Reporting Automation|Compliance Documentation|Cross-team Coordination',
                   'Supervised back-office executives and daily workflows|Improved documentation and approval processes|Controlled billing cycles and payment tracking|Automated recurring MIS reports'),
        senior=_level('Back-Office Leadership|Process Standardisation|Budget Tracking|Stakeholder Management|Audit Readiness|Team Development',
                      'Led the back-office function for one or more projects|Standardised processes, templates and controls|Prepared management reports and supported audits|Developed and trained the back-office team'),
    ),
    _role(
        'Project Coordinator', 'tech', 'people', PROJECTS, 'Schedules, teams and follow-ups',
        'Project Coordinators keep everyone aligned. You track tasks and deadlines, organise meetings, chase '
        'approvals and make sure information flows between site, office and client.',
        'Maintain schedules, trackers and meeting minutes|Follow up on tasks, approvals and deliveries|'
        'Coordinate between teams and vendors|Prepare progress updates and documentation',
        'Scheduling & Tracking|MS Office / Excel|Documentation|Communication|Time Management|Vendor Coordination|Reporting|Multitasking',
        'Trainee Coordinator|Project Coordinator|Senior Coordinator|Project Manager|Project Director',
        fields=[
            ('Scheduling & tracking', 'Project trackers|Gantt charts|Deadline tracking|MS Project|Look-ahead plans'),
            ('Documentation', 'Minutes of meetings|Correspondence|Document control|Reports'),
            ('Communication', 'Client communication|Email drafting|Meeting coordination|Follow-ups'),
            ('Office tools', 'MS Excel|MS Word|PowerPoint|SharePoint|Trello / Asana'),
            ('Vendor & logistics coordination', 'Vendor follow-up|Delivery tracking|Purchase requests|Approvals'),
            ('Reporting', 'Progress reports|Weekly updates|Dashboards'),
        ],
        recommended='MS Project|Power BI|SharePoint|Risk Tracking|Presentation Skills|Agile Basics',
        certifications='CAPM|PRINCE2 Foundation|Microsoft Office Specialist|Agile / Scrum Fundamentals',
        focus='scheduling, documentation and team communication', knowledge='project coordination',
        goal='well-organised project delivery',
        fresher=_level('MS Office|Scheduling Basics|Documentation|Communication|Time Management|Teamwork',
                       'Maintained trackers and schedules for academic or event projects|Prepared meeting minutes and follow-up lists|Coordinated communication between team members|Compiled reports and presentations',
                       'Event planning and coordination project|Project tracker and dashboard in Excel|Process documentation for a college or internship project',
                       'Project management fundamentals course|MS Project training|Business communication course|Advanced Excel course'),
        early=_level('Schedule Tracking|Meeting Coordination|Document Control|Vendor Follow-up|Progress Reporting|Approval Tracking',
                     'Maintained project schedules, trackers and action logs|Organised meetings and circulated minutes|Followed up on approvals, deliveries and open items|Prepared weekly progress reports'),
        mid=_level('Multi-project Coordination|Stakeholder Communication|Risk & Issue Tracking|Process Improvement|Reporting Dashboards|Supporting Project Managers',
                   'Coordinated multiple projects or work packages|Tracked risks, issues and decisions|Improved reporting templates and coordination processes|Supported project managers in planning and client communication'),
        senior=_level('Project Office (PMO) Management|Governance & Reporting|Team Coordination|Stakeholder Management|Planning Standards|Resource Coordination',
                      'Managed project coordination or PMO activities across projects|Set reporting, document and governance standards|Coordinated resources and priorities with project managers|Prepared portfolio status reports for management'),
    ),
    _role(
        'Project Director', 'tech', 'crown', PROJECTS, 'Portfolio leadership and strategy',
        'Project Directors oversee multiple large projects and the managers who run them. You set direction, secure '
        'client relationships, control profitability and take final responsibility for delivery.',
        'Lead the project portfolio and senior managers|Own budgets, profitability and client relations|'
        'Approve strategy, contracts and major decisions|Drive safety, quality and governance standards',
        'Strategic Planning|Contract & Claims Management|Financial Management|Executive Leadership|Client Relations|Risk & Governance|Negotiation|Decision Making',
        'Project Manager|Senior Project Manager|Project Director|Regional Director|VP / COO',
        fields=[
            ('Strategic planning', 'Portfolio planning|Business planning|Bid / no-bid decisions|Resource strategy'),
            ('Contracts & claims', 'FIDIC contracts|Claims management|Dispute resolution|Contract negotiation'),
            ('Financial management', 'P&L management|Budget approval|Cash flow management|Cost control'),
            ('Leadership', 'Executive leadership|Team building|Succession planning|Change management'),
            ('Client & stakeholder relations', 'Client relationship management|Board reporting|Authority liaison|Partner management'),
            ('Governance & risk', 'Risk governance|HSE leadership|Quality governance|Compliance'),
        ],
        recommended='Business Development|Risk Governance|Claims Management|Financial Analysis|Change Management|ESG Awareness',
        certifications='Project Management Professional (PMP)|PRINCE2 Practitioner|Program Management Professional (PgMP)|'
                       'NEBOSH IGC|Executive Management Programme',
        focus='project management, leadership and commercial principles', knowledge='project leadership',
        goal='successful delivery of complex projects',
        fresher=_level('Project Management Fundamentals|Leadership Basics|Business Communication|Financial Basics|Teamwork|Problem-solving',
                       'Supported project teams with planning and documentation|Prepared reports and presentations for management reviews|Coordinated information between teams|Learned project governance and reporting practices',
                       'Strategic plan for a sample infrastructure project (academic)|Feasibility study and financial analysis of a project|Case study on contract claims and disputes',
                       'Project management course|Leadership development programme|Contract management training|Finance for non-finance managers'),
        early=_level('Project Planning|Contract Basics|Cost Control|Client Coordination|Reporting|Team Coordination',
                     'Supported project leadership in planning and reporting|Coordinated client meetings and correspondence|Tracked project costs and contract obligations|Prepared management presentations'),
        mid=_level('Project Management|Commercial Management|Risk Management|Team Leadership|Client Relations|Contract Administration',
                   'Managed projects or major packages with defined budgets|Handled contract administration and variations|Led project teams and subcontractors|Reported performance to senior leadership'),
        senior=_level('Portfolio Leadership|P&L Ownership|Executive Stakeholder Management|Contract & Claims Strategy|Governance & HSE Leadership|Business Development',
                      'Led a portfolio of projects and project managers|Owned budgets, profitability and commercial outcomes where applicable|Managed executive client relationships and negotiations|Set governance, safety and quality standards across projects'),
    ),
    _role(
        'HSE Engineer', 'tech', 'shield', 'Oil & Gas, Construction & Energy', 'Health, safety and environment',
        'HSE Engineers keep people, assets and the environment safe on site. You identify hazards, run inspections '
        'and audits, manage permits and investigate incidents so work is completed safely and in line with regulations.',
        'Conduct risk assessments, HIRA and job safety analyses|Carry out site safety inspections and audits|'
        'Manage permit-to-work systems and toolbox talks|Report and investigate incidents and near misses',
        'Risk Assessment (HIRA / JSA)|Safety Inspections|Incident Investigation|Permit-to-Work Systems|Safety Audits|HSE Regulations|Emergency Response|Safety Training',
        'HSE Trainee|HSE Officer|HSE Engineer|Senior HSE Engineer|HSE Manager',
        fields=[
            ('Risk assessment', 'HIRA|Job safety analysis (JSA)|Risk matrix|Method statement review|Hazard identification'),
            ('Safety inspections', 'Daily site inspections|Scaffolding inspection|Lifting equipment checks|Electrical safety checks|PPE compliance checks|Fire safety inspection'),
            ('Incident reporting', 'Incident reporting|Near-miss reporting|Root cause analysis|Corrective & preventive actions (CAPA)|Incident statistics'),
            ('Permit-to-work systems', 'Hot work permits|Confined space entry|Work at height permits|Electrical isolation (LOTO)|Excavation permits'),
            ('Safety audits', 'Internal HSE audits|ISO 45001 audits|ISO 14001 awareness|Audit reports|Compliance tracking'),
            ('Training & emergency response', 'Toolbox talks|Induction training|Emergency drills|First aid|Fire fighting'),
        ],
        recommended='ISO 45001|Behaviour-Based Safety|Environmental Management|Fire Safety|Process Safety (Oil & Gas)|HSE Software',
        certifications='NEBOSH International General Certificate (IGC)|NEBOSH International Diploma|IOSH Managing Safely|'
                       'OSHA 30-Hour|ISO 45001 Lead Auditor|First Aid / CPR Certification',
        focus='workplace safety, hazard identification and safety regulations', knowledge='health, safety and environment',
        goal='safe and compliant site operations',
        fresher=_level('Hazard Identification|Safety Regulations Awareness|PPE Compliance|Basic First Aid|Report Writing|Communication',
                       'Assisted in site safety inspections during an internship or site training|Supported toolbox talks and safety inductions|Recorded observations and near misses|Helped maintain safety records and checklists',
                       'HIRA for a construction or industrial activity (academic)|Fire safety audit of a building|Study of incident causes and preventive measures|Emergency response plan for a facility',
                       'NEBOSH International General Certificate (IGC)|IOSH Managing Safely|First Aid and CPR training|Fire safety and fire fighting training|OSHA 30-Hour course'),
        early=_level('Site Safety Inspections|Permit-to-Work Management|Toolbox Talks|Incident Reporting|HSE Documentation|Safety Training Delivery',
                     'Conducted daily site inspections and recorded observations|Issued and monitored work permits for high-risk activities|Delivered toolbox talks and safety inductions|Reported incidents and near misses and tracked closure actions'),
        mid=_level('Risk Assessment Leadership|Incident Investigation & RCA|HSE Audits|Contractor Safety Management|HSE Statistics & KPIs|Emergency Preparedness',
                   'Prepared and reviewed risk assessments and method statements|Investigated incidents and recommended corrective actions|Conducted internal HSE audits and inspections|Monitored contractor safety performance and HSE KPIs'),
        senior=_level('HSE Management Systems|ISO 45001 / 14001 Implementation|HSE Leadership|Regulatory Compliance|Safety Culture Programmes|Stakeholder Management',
                      'Led HSE programmes across a site or multiple projects|Implemented or maintained HSE management systems|Represented HSE with clients, authorities and auditors|Led safety culture and behaviour-based safety initiatives'),
        experience_label='Site Experience',
    ),
    _role(
        'QA/QC Engineer', 'tech', 'search', 'Oil & Gas, Construction & Manufacturing', 'Quality assurance and inspection',
        'QA/QC Engineers make sure materials and workmanship meet specifications and standards. You plan inspections, '
        'review test results, raise non-conformances and keep quality records audit-ready.',
        'Prepare and follow inspection and test plans (ITPs)|Inspect materials, workmanship and installations|'
        'Raise and close non-conformance reports (NCRs)|Maintain quality records and support audits',
        'Inspection & Test Plans|Material Inspection|NDT Awareness|Quality Documentation|ISO 9001|Welding Inspection Basics|Calibration Control|Report Writing',
        'QC Trainee|QC Inspector|QA/QC Engineer|Senior QA/QC Engineer|QA/QC Manager',
        fields=[
            ('Inspection & testing', 'Incoming material inspection|Dimensional inspection|Visual inspection|Witnessing tests|Hydrotest / pressure testing'),
            ('Quality documentation', 'ITPs|Method statements|Inspection reports|NCRs|Quality dossiers'),
            ('Standards & codes', 'ISO 9001|ASME|API|ASTM|AWS D1.1|IS codes'),
            ('Welding & NDT', 'Welding inspection|WPS / PQR review|Radiography (RT)|Ultrasonic testing (UT)|Magnetic particle (MT)|Dye penetrant (PT)'),
            ('Quality systems', 'Internal audits|Calibration control|Root cause analysis|CAPA|Quality KPIs'),
            ('Tools', 'MS Excel|Measuring instruments|Quality software'),
        ],
        recommended='Six Sigma|Statistical Process Control|Coating Inspection|API Standards|Supplier Audits|Quality Software',
        certifications='ISO 9001 Lead Auditor|CSWIP 3.1 Welding Inspector|AWS Certified Welding Inspector (CWI)|'
                       'ASNT NDT Level II|API 510 / 570|Six Sigma Green Belt',
        focus='quality standards, inspection methods and documentation', knowledge='quality assurance and control',
        goal='consistent, specification-compliant work',
        fresher=_level('Quality Concepts (QA vs QC)|Reading Drawings & Specifications|Measuring Instruments|ISO 9001 Awareness|Report Writing|Attention to Detail',
                       'Assisted inspections of materials and workmanship during training|Recorded inspection results in checklists|Helped prepare inspection reports|Studied applicable codes and standards',
                       'Quality inspection checklist for a fabrication activity|Study of welding defects and NDT methods|Statistical process control case study|Root cause analysis of a quality issue',
                       'ISO 9001 Internal Auditor training|NDT Level II (RT / UT / MT / PT) training|Welding inspection course (CSWIP / AWS)|Quality management course'),
        early=_level('Material Inspection|ITP Implementation|NCR Reporting|Test Witnessing|Quality Records|Calibration Tracking',
                     'Inspected incoming materials and work in progress against specifications|Implemented ITPs and witnessed tests|Raised NCRs and followed up on corrective actions|Maintained inspection records and quality dossiers'),
        mid=_level('Quality Planning|Vendor / Subcontractor Quality|Root Cause Analysis|Internal Audits|Client Inspections|Mentoring Inspectors',
                   'Prepared quality plans and ITPs for projects or products|Coordinated client and third-party inspections|Performed root cause analysis and tracked CAPA|Conducted internal audits and quality reviews'),
        senior=_level('QMS Leadership|Quality Strategy|Supplier Quality Management|Audit & Certification|Team Leadership|Stakeholder Management',
                      'Led the QA/QC function for projects or a facility|Maintained the quality management system and certifications|Managed supplier and subcontractor quality performance|Reported quality performance to management and clients'),
    ),
    _role(
        'Electrical Engineer', 'tech', 'bolt', 'Energy, Power & Utilities', 'Power systems and electrical works',
        'Electrical Engineers design, install, test and maintain electrical systems — from power distribution and '
        'substations to plant and building services. You make sure systems are safe, efficient and compliant.',
        'Design and review electrical layouts and load calculations|Supervise installation, testing and commissioning|'
        'Maintain electrical equipment and troubleshoot faults|Ensure compliance with electrical safety standards',
        'Electrical Design|Load Calculations|AutoCAD Electrical|Testing & Commissioning|Switchgear & Transformers|Electrical Safety|PLC Basics|Maintenance & Troubleshooting',
        'Graduate Engineer|Electrical Engineer|Senior Electrical Engineer|Electrical Lead|Engineering Manager',
        fields=[
            ('Design & calculations', 'Load calculations|Cable sizing|Single line diagrams (SLD)|Lighting design|Earthing design|Short-circuit studies'),
            ('Electrical equipment', 'Transformers|Switchgear|Motors|DG sets|UPS|Panels & MCCs'),
            ('Testing & commissioning', 'Insulation resistance testing|Relay testing|Pre-commissioning checks|Commissioning|Protection systems'),
            ('Tools & software', 'AutoCAD Electrical|ETAP|DIALux|EPLAN|MS Excel'),
            ('Automation', 'PLC programming|SCADA|VFDs|Instrumentation basics'),
            ('Safety & standards', 'LOTO|Electrical safety|IEC standards|IS / IEEE standards|Permit-to-work'),
        ],
        recommended='ETAP|Solar PV Design|SCADA|Energy Auditing|Protection Relays|Primavera P6',
        certifications='Electrical Supervisor Licence|AutoCAD Electrical Certification|ETAP Certification|'
                       'PLC / SCADA Certification|NEBOSH IGC|Certified Energy Manager',
        focus='power systems, electrical design and safety standards', knowledge='electrical engineering',
        goal='safe and reliable electrical systems',
        fresher=_level('Electrical Fundamentals|AutoCAD Electrical Basics|Wiring & Circuit Reading|Electrical Safety Awareness|Measuring Instruments|PLC Basics',
                       'Assisted in electrical installation and testing during internships|Read and interpreted single line and wiring diagrams|Supported maintenance checks on electrical equipment|Recorded test results and observations',
                       'Solar PV system design for a building|Load calculation and SLD for a small facility|PLC-based automation of a process (academic)|Energy audit of a campus building',
                       'AutoCAD Electrical training|PLC and SCADA training|Electrical safety course|Substation or plant internship'),
        early=_level('Installation Supervision|Testing & Commissioning|Preventive Maintenance|Fault Troubleshooting|Cable Sizing|Documentation',
                     'Supervised installation of panels, cabling and equipment|Performed testing and supported commissioning|Carried out preventive maintenance and fault diagnosis|Prepared test reports and as-built documents'),
        mid=_level('Electrical System Design|Protection & Relay Coordination|Energy Efficiency|Contractor Coordination|Project Execution|Mentoring Engineers',
                   'Designed electrical systems and prepared calculations and SLDs|Led testing and commissioning of electrical packages|Improved energy efficiency and reliability of systems|Coordinated contractors, vendors and consultants'),
        senior=_level('Electrical Engineering Leadership|Power System Studies|Asset Management|Regulatory Compliance|Team Leadership|Budget & Vendor Management',
                      'Led electrical engineering for projects or facilities|Reviewed power system studies and major designs|Managed electrical assets, maintenance strategy and compliance|Managed teams, vendors and budgets for electrical works'),
    ),
    _role(
        'Mechanical Engineer', 'tech', 'gear', 'Manufacturing & Plant Operations', 'Machines, maintenance and production',
        'Mechanical Engineers design, build and maintain machines and mechanical systems. In manufacturing and plants '
        'you keep equipment running, improve production processes and solve technical problems on the shop floor.',
        'Maintain and troubleshoot machines and mechanical equipment|Plan preventive and breakdown maintenance|'
        'Support production and process improvements|Prepare drawings, reports and maintenance records',
        'Mechanical Design|AutoCAD / SolidWorks|Preventive Maintenance|Manufacturing Processes|Root Cause Analysis|GD&T|Hydraulics & Pneumatics|Safety Practices',
        'Graduate Engineer Trainee|Mechanical Engineer|Senior Engineer|Maintenance / Production Manager|Plant Head',
        fields=[
            ('Design & drafting', 'AutoCAD|SolidWorks|CATIA|Creo|GD&T|3D modelling'),
            ('Maintenance', 'Preventive maintenance|Breakdown maintenance|Predictive maintenance|Lubrication schedules|Spare parts management'),
            ('Manufacturing processes', 'Machining|Welding & fabrication|Casting|Sheet metal|CNC operations'),
            ('Equipment & systems', 'Pumps|Compressors|Hydraulics & pneumatics|HVAC|Boilers|Conveyors'),
            ('Improvement methods', 'Root cause analysis|5S|Kaizen|Lean manufacturing|TPM|Six Sigma'),
            ('Safety & documentation', 'LOTO|Maintenance records|SOPs|Work permits|SAP PM'),
        ],
        recommended='SAP PM|Condition Monitoring|TPM|Six Sigma|Energy Conservation|Project Management Basics',
        certifications='Certified SolidWorks Associate (CSWA)|Six Sigma Green Belt|TPM Certification|'
                       'Certified Maintenance & Reliability Professional (CMRP)|NEBOSH IGC',
        focus='mechanical design, manufacturing processes and maintenance', knowledge='mechanical engineering',
        goal='efficient, safe and reliable operations',
        fresher=_level('Engineering Drawing|AutoCAD / SolidWorks Basics|Manufacturing Processes|Basic Maintenance Practices|Safety Awareness|Teamwork',
                       'Assisted maintenance teams during an internship or industrial training|Observed and documented production processes|Prepared drawings and 3D models under guidance|Recorded equipment checks and readings',
                       'Design and fabrication of a mechanical prototype|3D model and analysis of a machine component|Preventive maintenance plan for a workshop|Lean / 5S implementation study',
                       'AutoCAD / SolidWorks training|Industrial training in a manufacturing plant|Lean manufacturing course|Hydraulics and pneumatics training'),
        early=_level('Preventive Maintenance|Breakdown Troubleshooting|Equipment Installation|Production Support|Maintenance Records|5S & Kaizen',
                     'Carried out preventive and breakdown maintenance of equipment|Diagnosed machine faults and coordinated repairs|Supported production with technical issue resolution|Maintained maintenance logs and spare parts records'),
        mid=_level('Maintenance Planning|Reliability Improvement|Root Cause Analysis|Process Improvement|Vendor Coordination|Mentoring Technicians',
                   'Planned maintenance schedules and spare parts|Reduced repeat breakdowns through root cause analysis|Led improvement projects on equipment or processes|Coordinated with vendors for repairs, overhauls and installations'),
        senior=_level('Plant Engineering Leadership|Asset Management|TPM / Lean Programmes|Capex Projects|Team Leadership|Budget Management',
                      'Led maintenance or engineering teams for a plant or section|Defined asset management and reliability strategy|Managed capital projects and equipment upgrades|Controlled maintenance budgets and vendor contracts'),
    ),

    # --------------------------------------------------- NON-IT NON-TECHNICAL
    _role(
        'HR Manager', 'nt', 'people', 'Human Resources', 'Lead people strategy and policy',
        'HR Managers shape how an organisation hires, develops and supports its people. You lead the HR team, build '
        'policies, handle employee relations and keep the company compliant with labour laws.',
        'Lead recruitment, onboarding and retention|Create and update HR policies|'
        'Handle employee relations and grievances|Oversee payroll, compliance and performance reviews',
        'Talent Management|Labour Law & Compliance|Employee Relations|Performance Management|Payroll Knowledge|Team Leadership|Conflict Resolution|HRMS Tools',
        'HR Executive|Senior HR Executive|HR Manager|Senior HR Manager|HR Head',
        fields=[
            ('Talent acquisition', 'Workforce planning|Recruitment strategy|Employer branding|Interview panels'),
            ('HR policy & compliance', 'HR policies|Labour law compliance|PF / ESI|Shops & Establishment Act|Statutory audits'),
            ('Employee relations', 'Grievance handling|Disciplinary process|Employee engagement|Exit interviews'),
            ('Performance & development', 'Performance appraisals|KPIs / KRAs|Training needs analysis|Succession planning'),
            ('Compensation & payroll', 'Payroll oversight|Salary benchmarking|Compensation structure|Benefits administration'),
            ('HR systems', 'HRMS (Zoho / Keka / SAP SuccessFactors)|HR analytics|MS Excel'),
        ],
        recommended='HR Analytics|Change Management|Organisational Development|Coaching|Diversity & Inclusion|Employer Branding',
        certifications='SHRM-CP / SHRM-SCP|CIPD Level 5 / 7|HR Analytics Certification|Labour Law Certification|Certified Compensation Professional',
        focus='human resource management, labour laws and people practices', knowledge='human resources',
        goal='positive, compliant workplaces',
        fresher=_level('HR Fundamentals|Labour Law Basics|Recruitment Basics|MS Excel|Communication|Confidentiality',
                       'Supported HR activities during internships|Maintained employee records and trackers|Assisted with recruitment and onboarding tasks|Prepared HR documents and letters',
                       'Study on employee engagement practices (MBA / academic)|Performance appraisal system design case study|Labour law compliance checklist',
                       'HR management certification course|Labour law and compliance training|HR analytics course|HR internship'),
        early=_level('Recruitment Coordination|Onboarding|HR Operations|Employee Engagement Activities|Attendance & Leave Management|HR Documentation',
                     'Coordinated recruitment and onboarding activities|Maintained HR records, policies and documentation|Organised employee engagement activities|Supported payroll inputs and statutory compliance'),
        mid=_level('HR Business Partnering|Performance Management|Employee Relations|Policy Development|Compliance Management|HR Analytics',
                   'Managed HR operations for a business unit or location|Ran performance appraisal cycles|Handled employee relations and grievance cases|Updated HR policies in line with labour laws'),
        senior=_level('HR Strategy|Organisational Development|Compensation & Benefits Strategy|Leadership Hiring|Change Management|HR Team Leadership',
                      'Led the HR function and HR team|Defined HR strategy, policies and organisational structure|Oversaw compensation, benefits and compliance|Advised leadership on people matters and change initiatives'),
    ),
    _role(
        'HR Executive', 'nt', 'clip', 'Human Resources', 'Day-to-day HR operations',
        'HR Executives run the daily work of the HR department. You maintain employee records, support hiring and '
        'onboarding, track attendance and answer staff queries.',
        'Maintain employee records and attendance|Support onboarding and exit formalities|'
        'Coordinate payroll inputs and leave data|Answer employee queries and update HRMS',
        'HR Operations|MS Excel|HRMS Software|Onboarding|Attendance & Leave|Communication|Documentation|Confidentiality',
        'HR Trainee|HR Executive|Senior HR Executive|HR Manager|HR Head',
        fields=[
            ('Recruitment', 'Sourcing support|Interview scheduling|Candidate follow-up|Offer letters|Job postings'),
            ('Employee onboarding', 'Joining formalities|Induction|Document verification|ID & access setup|Background verification'),
            ('HR operations', 'Employee records|Attendance & leave|HR letters|Exit formalities|Policy communication'),
            ('Employee engagement', 'Engagement activities|Celebrations & events|Feedback surveys|Employee queries'),
            ('Payroll knowledge', 'Payroll inputs|PF & ESI|Salary structure basics|Full & final settlement'),
            ('HR software', 'Zoho People|Keka|greytHR|SAP SuccessFactors|MS Excel'),
        ],
        recommended='Payroll Processing|HR Analytics|Labour Law Basics|Employee Engagement|Recruitment Tools|Power BI Basics',
        certifications='HR Generalist Certification|Payroll Management Certification|SHRM-CP|Advanced Excel Certification',
        focus='HR operations, recruitment and employee support', knowledge='human resources',
        goal='smooth HR operations and a positive employee experience',
        fresher=_level('HR Fundamentals|MS Excel|Recruitment Basics|Onboarding Basics|Communication|Confidentiality',
                       'Maintained employee records during an HR internship|Scheduled interviews and coordinated with candidates|Assisted with joining formalities and induction|Prepared HR letters and documents',
                       'Study on the recruitment and selection process (academic)|Employee onboarding checklist design|Employee satisfaction survey and analysis',
                       'HR generalist certification course|Payroll and statutory compliance training|Advanced Excel course|HR internship'),
        early=_level('HR Operations|Attendance & Leave Management|Payroll Inputs|Onboarding & Exit|Employee Query Handling|HRMS Administration',
                     'Maintained employee records and HRMS data|Managed attendance, leave and payroll inputs|Handled onboarding, induction and exit formalities|Resolved employee queries on policies and benefits'),
        mid=_level('HR Generalist Operations|Statutory Compliance|Engagement Programmes|Process Improvement|HR Reporting|Recruitment Coordination',
                   'Handled end-to-end HR operations for a location or business unit|Ensured PF, ESI and statutory compliance|Planned and ran engagement initiatives|Prepared HR MIS reports and improved HR processes'),
        senior=_level('HR Team Supervision|Policy Implementation|Employee Relations|HR Analytics|Stakeholder Management|Audit & Compliance',
                      'Supervised HR executives and HR operations|Implemented HR policies and process changes|Handled employee relations cases|Prepared HR analytics and audit documentation'),
    ),
    _role(
        'HR Recruiter', 'nt', 'search', 'Human Resources', 'Sourcing and hiring talent',
        'HR Recruiters find and hire the right people. You source candidates, screen resumes, schedule interviews and '
        'guide candidates through to the offer.',
        'Understand job requirements from hiring managers|Source candidates via portals, social media and referrals|'
        'Screen resumes and conduct first-round interviews|Coordinate interviews, offers and joining',
        'Sourcing|Resume Screening|Job Portals (Naukri, LinkedIn)|Interviewing|Communication|Negotiation|ATS Tools|Target Orientation',
        'Recruitment Trainee|HR Recruiter|Senior Recruiter|Talent Acquisition Lead|TA Manager',
        fields=[
            ('Sourcing', 'Job portals (Naukri / Indeed)|LinkedIn Recruiter|Boolean search|Employee referrals|Social media sourcing|Campus hiring'),
            ('Screening', 'Resume screening|Telephonic screening|Competency-based interviewing|Assessment coordination'),
            ('Hiring coordination', 'Interview scheduling|Hiring manager coordination|Offer negotiation|Joining follow-up'),
            ('Recruitment domains', 'IT recruitment|Non-IT recruitment|Bulk / volume hiring|Leadership hiring'),
            ('Recruitment tools', 'ATS (Zoho Recruit / Greenhouse)|MS Excel|Recruitment dashboards'),
            ('Candidate experience', 'Candidate communication|Employer branding|Feedback management'),
        ],
        recommended='Boolean Search|Recruitment Analytics|Employer Branding|Assessment Tools|Negotiation|Campus Hiring',
        certifications='LinkedIn Certified Professional – Recruiter|AIRS Certified Internet Recruiter|SHRM-CP|Talent Acquisition Certification',
        focus='sourcing, screening and candidate communication', knowledge='recruitment',
        goal='hiring the right talent efficiently',
        fresher=_level('Sourcing Basics|Resume Screening|Job Portals|Communication|MS Excel|Persistence',
                       'Sourced candidates on job portals during an internship|Screened resumes against job requirements|Scheduled interviews and followed up with candidates|Maintained recruitment trackers',
                       'Study on recruitment channels and effectiveness (academic)|Recruitment tracker and dashboard in Excel|Campus hiring plan for a sample company',
                       'Recruitment and talent acquisition course|LinkedIn Recruiter training|HR internship'),
        early=_level('End-to-end Recruitment|Boolean Sourcing|Interview Coordination|Offer Management|Recruitment Reporting|ATS Management',
                     'Managed end-to-end recruitment for assigned positions|Sourced candidates through portals, LinkedIn and referrals|Coordinated interviews with hiring managers|Rolled out offers and tracked joining'),
        mid=_level('Niche / Leadership Hiring|Stakeholder Management|Recruitment Metrics|Employer Branding|Campus Programmes|Mentoring Recruiters',
                   'Hired for niche or senior positions|Managed hiring manager relationships and expectations|Tracked recruitment metrics such as time-to-hire|Planned campus or bulk hiring drives'),
        senior=_level('Talent Acquisition Strategy|Recruitment Team Leadership|Workforce Planning|Vendor / Agency Management|Hiring Analytics|Employer Branding Strategy',
                      'Led a recruitment team or talent acquisition function|Planned hiring with business leaders|Managed recruitment agencies and budgets|Built employer branding and hiring processes'),
    ),
    _role(
        'Back Office Executive', 'nt', 'brief', 'Administration', 'Data entry, records and support',
        'Back Office Executives keep the business running behind the scenes. You enter and verify data, prepare '
        'documents, handle emails and support the front-line and management teams.',
        'Enter, verify and update data accurately|Prepare invoices, reports and documents|'
        'Handle emails, calls and coordination|Maintain files and digital records',
        'Data Entry|MS Excel & Word|Typing Speed & Accuracy|Email Handling|ERP / Tally Basics|Documentation|Time Management|Attention to Detail',
        'Data Entry Operator|Back Office Executive|Senior Executive|Back Office Manager|Operations Manager',
        fields=[
            ('Data entry & verification', 'Data entry|Data verification|Typing speed|Data cleansing|Record updates'),
            ('MS Office', 'MS Excel|VLOOKUP & pivot tables|MS Word|PowerPoint|Google Sheets'),
            ('Documentation', 'Invoices|Reports|Filing systems|Digital records|Document scanning'),
            ('Communication', 'Email handling|Phone coordination|Customer follow-up|Internal coordination'),
            ('Software', 'Tally basics|ERP / SAP basics|CRM systems'),
            ('Work habits', 'Accuracy|Time management|Confidentiality'),
        ],
        recommended='Advanced Excel|Tally Prime|CRM Tools|Google Workspace|MIS Reporting|Power BI Basics',
        certifications='Microsoft Office Specialist (Excel)|Tally Certification|Typing Speed Certificate|SAP End User Certification',
        focus='data management, documentation and office tools', knowledge='back-office operations',
        goal='accurate, efficient business operations',
        fresher=_level('Data Entry|MS Excel Basics|Typing Speed & Accuracy|Email Writing|Documentation|Time Management',
                       'Entered and verified data during an internship or training|Maintained files and digital records|Prepared simple reports in Excel|Handled emails and follow-ups',
                       'Inventory or student records database in Excel|Office filing system reorganisation|Data cleaning exercise on a sample dataset',
                       'Advanced Excel course|Typing certification|Tally / ERP basics training|Office administration course'),
        early=_level('Data Management|Report Preparation|Invoice Processing|ERP Data Entry|Email & Call Coordination|Records Management',
                     'Entered, verified and updated data with high accuracy|Prepared invoices, reports and documents|Handled emails, calls and internal coordination|Maintained physical and digital records'),
        mid=_level('Process Efficiency|MIS Reporting|Quality Checks|Training New Staff|Cross-team Coordination|ERP Administration',
                   'Prepared MIS reports for management|Checked data quality and corrected errors|Trained new executives on processes|Improved data handling and reporting processes'),
        senior=_level('Back-Office Supervision|Process Improvement|Workflow Management|Reporting|Team Coordination|Audit Support',
                      'Supervised daily back-office workflow and output|Standardised processes and checklists|Supported audits and compliance documentation|Coordinated with management on reporting needs'),
    ),
    _role(
        'Admin Executive', 'nt', 'brief', 'Administration & Facilities', 'Office administration and facilities',
        'Admin Executives keep the office running smoothly. You manage facilities, supplies, travel and vendor '
        'services, maintain records and support employees and management with day-to-day administration.',
        'Manage office facilities, supplies and housekeeping|Coordinate travel, events and meeting arrangements|'
        'Handle vendors, AMC contracts and utility bills|Maintain administrative records and correspondence',
        'Office Administration|Facility Management|Vendor Management|MS Office|Travel Coordination|Record Keeping|Communication|Problem Solving',
        'Admin Assistant|Admin Executive|Senior Admin Executive|Admin Manager|Head of Administration',
        fields=[
            ('Office administration', 'Office supplies|Correspondence|Front desk coordination|Visitor management|Courier management'),
            ('Facility management', 'Housekeeping|Security coordination|Maintenance requests|Asset management|Utility management'),
            ('Vendor management', 'Vendor coordination|AMC contracts|Bill processing|Quotations'),
            ('Travel & events', 'Travel booking|Hotel arrangements|Event coordination|Meeting arrangements'),
            ('Records & tools', 'MS Excel|MS Word|Filing systems|Asset registers|ERP basics'),
            ('Communication', 'Email drafting|Phone etiquette|Employee support'),
        ],
        recommended='Facility Management|Budgeting|Event Management|Contract Management|ERP Basics|Safety Compliance',
        certifications='Office Administration Certification|Facility Management Professional (IFMA FMP)|Advanced Excel Certification',
        focus='office administration, coordination and communication', knowledge='administration',
        goal='efficient, well-organised office operations',
        fresher=_level('MS Office|Communication|Record Keeping|Time Management|Coordination|Problem-solving',
                       'Supported office administration during an internship|Maintained files and records|Coordinated meeting and event arrangements|Handled emails and phone calls',
                       'Office supplies tracker in Excel|College event coordination|Asset register for a department',
                       'Office administration course|Advanced Excel course|Business communication training'),
        early=_level('Facility Coordination|Vendor Follow-up|Travel Arrangements|Office Supplies Management|Bill Processing|Asset Records',
                     'Managed office supplies, housekeeping and facility requests|Booked travel and accommodation for employees|Coordinated with vendors and processed bills|Maintained asset and administrative records'),
        mid=_level('Facility Management|AMC & Contract Management|Budget Tracking|Event Management|Process Improvement|Supervising Support Staff',
                   'Managed facilities and services for an office or site|Negotiated and tracked AMC and service contracts|Tracked admin expenses against budget|Supervised housekeeping, security and support staff'),
        senior=_level('Administration Management|Budget Ownership|Vendor Strategy|Compliance|Team Leadership|Workplace Planning',
                      'Led administration for one or more offices|Owned admin budgets and vendor contracts where applicable|Ensured statutory and safety compliance for facilities|Planned workplace moves, expansions and policies'),
    ),
    _role(
        'Operations Executive', 'nt', 'gear', 'Operations & Logistics', 'Daily operations and process support',
        'Operations Executives make sure daily business processes run on time and as planned. You track orders and '
        'service levels, coordinate between teams, solve operational issues and keep reports accurate.',
        'Monitor daily operations, orders and service levels|Coordinate between sales, stores, logistics and customers|'
        'Resolve operational issues and escalations|Prepare operations MIS and performance reports',
        'Operations Coordination|MIS Reporting|Advanced Excel|Process Adherence|Problem Solving|ERP Systems|Communication|Time Management',
        'Operations Trainee|Operations Executive|Senior Operations Executive|Operations Manager|Head of Operations',
        fields=[
            ('Operations coordination', 'Order processing|Dispatch coordination|Service level tracking|Escalation handling|Shift coordination'),
            ('Reporting', 'MIS reports|Advanced Excel|Dashboards|KPI tracking'),
            ('Process management', 'SOP adherence|Process documentation|Quality checks|Process improvement'),
            ('Logistics', 'Shipment tracking|Transport coordination|Delivery scheduling|Inventory coordination'),
            ('Systems', 'ERP / SAP|CRM|Google Sheets|Ticketing tools'),
            ('Customer & team coordination', 'Customer communication|Vendor coordination|Team coordination'),
        ],
        recommended='Lean Six Sigma|Power BI|Process Mapping|Supply Chain Basics|Vendor Management|Customer Service',
        certifications='Lean Six Sigma Yellow / Green Belt|Advanced Excel Certification|Operations Management Certificate|SAP End User Certification',
        focus='business operations, coordination and reporting', knowledge='operations',
        goal='efficient, reliable day-to-day operations',
        fresher=_level('MS Excel|Communication|Process Orientation|Coordination|Problem-solving|Time Management',
                       'Supported daily operations during an internship|Tracked orders or tasks in trackers|Prepared simple MIS reports|Coordinated with teams to resolve issues',
                       'Operations dashboard in Excel|Process mapping of an order-to-delivery cycle (academic)|Logistics cost study',
                       'Operations management course|Advanced Excel / MIS training|Supply chain basics course'),
        early=_level('Order & Dispatch Coordination|MIS Reporting|Escalation Handling|SOP Adherence|ERP Updates|Vendor Coordination',
                     'Coordinated daily orders, dispatches and service requests|Prepared operations MIS and KPI reports|Resolved escalations with relevant teams|Ensured processes followed SOPs'),
        mid=_level('Process Improvement|KPI Management|Team Coordination|Cost Control|Vendor Management|Training New Staff',
                   'Owned operations for a process, region or client|Improved turnaround time or accuracy through process changes|Tracked KPIs and drove corrective actions|Coordinated vendors and service partners'),
        senior=_level('Operations Management|Team Leadership|Capacity Planning|Budget Tracking|Stakeholder Management|Process Excellence',
                      'Managed operations teams and service delivery|Planned capacity and resources|Led process excellence initiatives|Reported operations performance to management'),
    ),
    _role(
        'Accountant', 'nt', 'calc', 'Finance & Accounts', 'Books, audit and compliance',
        'Accountants record and check a company’s financial transactions. You maintain books, reconcile accounts, '
        'handle GST and TDS filings and prepare financial statements.',
        'Maintain ledgers, journals and books of accounts|Reconcile bank and vendor statements|'
        'Handle GST, TDS and statutory filings|Prepare monthly and annual financial reports',
        'Tally / Accounting Software|GST & TDS|Bank Reconciliation|Financial Statements|Advanced Excel|Accounting Principles|Auditing Basics|Accuracy',
        'Accounts Assistant|Accountant|Senior Accountant|Accounts Manager|Finance Controller',
        fields=[
            ('Bookkeeping', 'Journal entries|Ledger maintenance|Accounts payable|Accounts receivable|Petty cash'),
            ('Taxation & compliance', 'GST returns|TDS|Income tax basics|Statutory compliance|E-invoicing'),
            ('Reconciliation', 'Bank reconciliation|Vendor reconciliation|Customer reconciliation|Inter-company reconciliation'),
            ('Financial reporting', 'Trial balance|Profit & loss|Balance sheet|Month-end closing|MIS reports'),
            ('Accounting software', 'Tally Prime|SAP FICO|Zoho Books|QuickBooks|MS Excel'),
            ('Audit', 'Audit support|Internal controls|Fixed asset register|Documentation'),
        ],
        recommended='SAP FICO|Advanced Excel|IFRS / Ind AS Basics|Payroll Accounting|Cost Accounting|Power BI',
        certifications='Tally Certification|CA Inter / CMA Inter (if applicable)|Certified Public Accountant (CPA)|ACCA|'
                       'GST Practitioner Certification|SAP FICO Certification',
        focus='accounting principles, taxation and financial reporting', knowledge='accounting',
        goal='accurate and compliant financial records',
        fresher=_level('Accounting Principles|Tally Basics|GST Basics|MS Excel|Bookkeeping|Accuracy',
                       'Recorded journal entries during an internship or articleship|Assisted with bank reconciliation|Helped prepare GST working papers|Organised vouchers and accounting documents',
                       'Accounts of a sample business in Tally (academic)|Financial statement analysis of a listed company|GST return preparation case study',
                       'Tally Prime with GST course|Advanced Excel course|Articleship or accounting internship|Income tax and TDS course'),
        early=_level('Bookkeeping|GST & TDS Filing|Bank Reconciliation|Accounts Payable / Receivable|Month-end Closing|Tally / ERP',
                     'Maintained books of accounts and ledgers|Prepared GST and TDS workings and filings|Performed bank and vendor reconciliations|Supported month-end closing and reporting'),
        mid=_level('Financial Reporting|Statutory Audit Support|Taxation|Internal Controls|Budget Tracking|Mentoring Accounts Staff',
                   'Prepared monthly and annual financial statements|Coordinated statutory and internal audits|Managed tax compliance and filings|Strengthened internal controls and documentation'),
        senior=_level('Accounts Management|Financial Controls|Budgeting & Forecasting|Audit Management|Team Leadership|Treasury / Cash Flow Management',
                      'Led the accounts team and closing process|Owned financial controls and audit readiness|Prepared budgets, forecasts and management reports|Managed cash flow, banking and compliance'),
    ),
    _role(
        'Account Executive', 'nt', 'wallet', 'Finance & Accounts', 'Client accounts and billing',
        'Account Executives manage billing, receivables and client accounts. You raise invoices, follow up on '
        'payments and keep client ledgers accurate and up to date.',
        'Raise invoices and credit notes|Follow up on outstanding payments|'
        'Reconcile client and vendor accounts|Support month-end closing and audits',
        'Invoicing & Billing|Accounts Receivable|Tally / ERP|MS Excel|Reconciliation|Communication|GST Basics|Follow-up Skills',
        'Accounts Trainee|Account Executive|Senior Account Executive|Accounts Manager|Finance Manager',
        fields=[
            ('Billing & invoicing', 'Invoice preparation|Credit / debit notes|E-invoicing|Billing schedules'),
            ('Receivables', 'Payment follow-up|Ageing reports|Collections|Customer ledgers'),
            ('Reconciliation', 'Customer reconciliation|Vendor reconciliation|Bank reconciliation'),
            ('Taxation', 'GST basics|TDS basics|E-way bills'),
            ('Accounting software', 'Tally Prime|ERP / SAP|Zoho Books|MS Excel'),
            ('Client communication', 'Client communication|Email follow-up|Dispute resolution'),
        ],
        recommended='Credit Control|SAP|Advanced Excel|Cash Flow Reporting|Negotiation|Zoho Books',
        certifications='Tally Certification|Advanced Excel Certification|GST Certification|SAP FICO End User',
        focus='billing, receivables and accounting fundamentals', knowledge='accounts',
        goal='accurate billing and timely collections',
        fresher=_level('Accounting Basics|Tally Basics|MS Excel|Invoicing Basics|GST Basics|Communication',
                       'Prepared invoices and entries during an internship|Assisted with ledger updates and reconciliations|Followed up on payments under supervision|Maintained billing records',
                       'Receivables ageing analysis in Excel|Billing process study for a sample business|GST invoice preparation case study',
                       'Tally Prime with GST course|Advanced Excel course|Accounts internship'),
        early=_level('Invoicing|Accounts Receivable|Payment Follow-up|Reconciliation|Ageing Reports|Tally / ERP',
                     'Raised invoices and credit notes accurately and on time|Followed up on outstanding payments with clients|Reconciled customer and vendor accounts|Prepared ageing and collection reports'),
        mid=_level('Collections Management|Credit Control|Month-end Support|Audit Support|Process Improvement|Key Client Accounts',
                   'Managed collections for a portfolio of client accounts|Monitored credit limits and overdue accounts|Supported month-end closing and audits|Improved billing and collection processes'),
        senior=_level('Receivables Leadership|Credit Policy|Cash Flow Reporting|Team Supervision|Client Relationship Management|Controls & Compliance',
                      'Led billing and receivables operations|Defined credit control and collection policies|Reported cash flow and receivables to management|Supervised accounts executives'),
    ),
    _role(
        'Sales Executive', 'nt', 'trend', 'Sales & Marketing', 'Win customers and close deals',
        'Sales Executives bring in customers and revenue. You find leads, present products, handle objections and '
        'close deals while building lasting relationships.',
        'Generate and follow up on leads|Present products and prepare quotations|'
        'Close deals and meet monthly targets|Maintain customer relationships and CRM data',
        'Lead Generation|Product Presentation|Negotiation|Communication|CRM Tools|Cold Calling|Target Achievement|Customer Handling',
        'Sales Trainee|Sales Executive|Senior Sales Executive|Sales Manager|Regional Sales Head',
        fields=[
            ('Lead generation', 'Cold calling|Prospecting|Referrals|LinkedIn outreach|Lead qualification'),
            ('Selling skills', 'Product presentation|Needs analysis|Objection handling|Negotiation|Closing'),
            ('Customer relationships', 'Account follow-up|After-sales support|Customer retention|Cross-selling'),
            ('Sales documentation', 'Quotations|Proposals|Sales reports|Order processing'),
            ('Sales tools', 'CRM (Salesforce / Zoho / HubSpot)|MS Excel|WhatsApp Business|Email outreach'),
            ('Sales domain', 'B2B sales|B2C sales|Retail sales|Inside sales|Field sales'),
        ],
        recommended='Consultative Selling|Salesforce / Zoho CRM|Digital Prospecting|Presentation Skills|Market Research|Key Account Management',
        certifications='Certified Sales Professional|HubSpot Sales Software Certification|Salesforce Certified Associate|Negotiation Skills Certificate',
        focus='sales fundamentals, customer communication and negotiation', knowledge='sales',
        goal='customer acquisition and revenue growth',
        fresher=_level('Communication|Customer Handling|Product Knowledge|MS Excel|Negotiation Basics|Persuasion',
                       'Supported sales or marketing activities during an internship|Contacted prospects and recorded responses|Prepared product information and quotations|Updated customer data and follow-up lists',
                       'Market survey and competitor analysis (academic)|Sales plan for a new product launch|Customer feedback study',
                       'Sales and negotiation training|CRM basics training|Business communication course|Sales internship'),
        early=_level('Lead Generation|Client Meetings|Quotation & Follow-up|Deal Closing|CRM Management|Target Achievement',
                     'Generated and qualified leads through calls, visits and referrals|Presented products and prepared quotations|Followed up and closed deals against monthly targets|Maintained customer records in CRM'),
        mid=_level('Key Account Handling|Consultative Selling|Pipeline Management|Upselling & Cross-selling|Market Insights|Mentoring New Executives',
                   'Managed a portfolio of key customer accounts|Built and managed a sales pipeline|Expanded business with existing clients|Shared market feedback with sales and product teams'),
        senior=_level('Sales Leadership|Territory Strategy|Strategic Accounts|Forecasting|Team Coaching|Business Development',
                      'Owned revenue for a territory, segment or key accounts|Coached and supported other sales team members|Prepared sales forecasts and plans|Developed new business channels or partnerships'),
    ),
    _role(
        'Sales Manager', 'nt', 'flag', 'Sales & Marketing', 'Lead teams and revenue targets',
        'Sales Managers lead the sales team and own revenue targets. You plan strategy, coach executives, review the '
        'pipeline and build key client relationships.',
        'Set targets and plan sales strategy|Coach and review the sales team|'
        'Track pipeline, forecasts and performance|Handle key accounts and negotiations',
        'Sales Strategy|Team Leadership|Pipeline Management|Negotiation|Forecasting|CRM Tools|Key Account Management|Presentation',
        'Sales Executive|Senior Executive|Sales Manager|Regional Manager|Sales Director',
        fields=[
            ('Sales strategy', 'Sales planning|Territory planning|Pricing strategy|Market expansion|Channel strategy'),
            ('Team leadership', 'Hiring sales staff|Coaching|Performance reviews|Incentive planning|Sales training'),
            ('Pipeline & forecasting', 'Pipeline reviews|Sales forecasting|Funnel analysis|Target setting'),
            ('Key accounts', 'Key account management|Contract negotiation|Client retention|Strategic partnerships'),
            ('Reporting & tools', 'CRM dashboards|Sales MIS|MS Excel|Power BI'),
            ('Market knowledge', 'Competitor analysis|Market research|Customer segmentation'),
        ],
        recommended='Sales Analytics|Channel Management|Strategic Negotiation|Power BI|Coaching|Business Planning',
        certifications='Certified Sales Leader|Salesforce Certified Administrator|Strategic Sales Management Programme|Negotiation Certification',
        focus='sales, team coordination and customer relationships', knowledge='sales management',
        goal='sustainable revenue growth',
        fresher=_level('Sales Fundamentals|Communication|Negotiation Basics|MS Excel|Teamwork|Presentation Skills',
                       'Supported sales team activities during an internship|Researched markets and potential customers|Prepared sales reports and presentations|Followed up on leads under guidance',
                       'Sales strategy for a product launch (MBA / academic)|Market segmentation study|Sales performance analysis in Excel',
                       'Sales management course|Negotiation training|CRM training'),
        early=_level('Lead Conversion|Client Relationship Management|Sales Reporting|Negotiation|CRM Tools|Target Achievement',
                     'Achieved individual sales targets for assigned products or territory|Managed client relationships and negotiations|Prepared sales reports and forecasts|Supported junior team members'),
        mid=_level('Team Supervision|Pipeline Management|Key Account Management|Sales Planning|Forecasting|Coaching',
                   'Supervised a sales team or territory|Reviewed pipelines and forecasts|Managed key accounts and negotiations|Planned sales activities and promotions'),
        senior=_level('Sales Strategy|Revenue Ownership|Team Leadership|Channel Development|Executive Negotiation|Business Planning',
                      'Owned revenue targets for a region, team or business line where applicable|Led and developed sales teams|Defined sales strategy, pricing and channels|Negotiated strategic contracts and partnerships'),
    ),
    _role(
        'Sales Officer', 'nt', 'cart', 'Sales & Marketing', 'Field sales and territory coverage',
        'Sales Officers cover a territory, visiting dealers and customers to sell products and collect orders. You '
        'build relationships, track market activity and report back regularly.',
        'Visit dealers, retailers and customers|Collect orders and ensure product availability|'
        'Collect payments and market feedback|Submit daily visit and sales reports',
        'Field Sales|Territory Management|Dealer Handling|Order Booking|Communication|Local Market Knowledge|Reporting|Persuasion',
        'Sales Trainee|Sales Officer|Senior Sales Officer|Area Sales Manager|Regional Manager',
        fields=[
            ('Field sales', 'Dealer visits|Retail visits|Beat planning|Order booking|Merchandising'),
            ('Territory management', 'Route planning|Market coverage|New dealer appointment|Distributor management'),
            ('Collections', 'Payment collection|Credit follow-up|Outstanding tracking'),
            ('Market intelligence', 'Competitor tracking|Market feedback|Scheme communication'),
            ('Reporting', 'Daily visit reports|Sales reports|DMS / SFA apps|MS Excel'),
            ('Communication', 'Local language skills|Persuasion|Relationship building'),
        ],
        recommended='Distribution Management|SFA / DMS Apps|Merchandising|Negotiation|Retail Analytics|Team Supervision',
        certifications='Field Sales Certification|Sales & Distribution Management Course|Negotiation Skills Certificate',
        focus='field sales, customer relationships and market knowledge', knowledge='field sales',
        goal='strong market coverage and sales growth',
        fresher=_level('Communication|Local Market Knowledge|Persuasion|Field Work Readiness|MS Excel Basics|Customer Handling',
                       'Supported field sales activities during an internship|Visited retailers to collect feedback or orders|Recorded visit details and orders|Communicated schemes and product information',
                       'Retail market survey in a local area|Distribution channel study for an FMCG product|Dealer satisfaction survey',
                       'Field sales training|Sales and communication course|Sales internship'),
        early=_level('Beat Planning|Order Booking|Dealer Relationship Management|Payment Collection|Market Reporting|Scheme Execution',
                     'Covered assigned beats and visited dealers and retailers|Booked orders and ensured product availability|Collected payments and followed up on outstanding amounts|Submitted daily visit and sales reports'),
        mid=_level('Territory Development|Distributor Management|New Dealer Appointment|Sales Planning|Competitor Analysis|Guiding Junior Officers',
                   'Developed new dealers and outlets in the territory|Managed distributor stock and orders|Planned promotions and schemes with the area manager|Tracked competitor activity and market trends'),
        senior=_level('Area Sales Management|Team Supervision|Channel Strategy|Target Planning|Key Distributor Management|Market Expansion',
                      'Managed sales for an area through officers or distributors|Planned targets and territory coverage|Opened new markets or channels|Reviewed team performance and market reports'),
    ),
    _role(
        'Sales & Marketing Executive', 'nt', 'mega', 'Sales & Marketing', 'Promote products and generate leads',
        'Sales & Marketing Executives combine selling with promotion. You plan campaigns, create outreach, generate '
        'leads and support the sales team with marketing material.',
        'Plan and run promotions and campaigns|Generate leads via digital and field channels|'
        'Prepare brochures, offers and presentations|Track campaign results and customer feedback',
        'Digital Marketing|Social Media|Lead Generation|Content Creation|Canva / Design Basics|Market Research|Communication|CRM Tools',
        'Marketing Trainee|Sales & Marketing Executive|Senior Executive|Marketing Manager|Head of Marketing',
        fields=[
            ('Digital marketing', 'Social media marketing|SEO basics|Google Ads|Meta Ads|Email marketing|WhatsApp marketing'),
            ('Content', 'Content writing|Canva designs|Brochures|Video basics|Copywriting'),
            ('Lead generation', 'Lead campaigns|Inbound leads|Cold outreach|Events & exhibitions|Lead qualification'),
            ('Analytics', 'Google Analytics|Campaign reporting|MS Excel|Market research'),
            ('Sales support', 'Presentations|Quotations|CRM updates|Customer follow-up'),
            ('Marketing tools', 'HubSpot|Zoho CRM|Mailchimp|Hootsuite / Buffer'),
        ],
        recommended='Google Ads|SEO|Marketing Automation|Video Editing|Analytics|Copywriting',
        certifications='Google Ads Certification|Google Analytics Certification|HubSpot Inbound Marketing|Meta Certified Digital Marketing Associate',
        focus='marketing fundamentals, digital media and customer communication', knowledge='sales and marketing',
        goal='brand growth and lead generation',
        fresher=_level('Social Media Basics|Canva|Communication|MS Excel|Content Writing|Market Research',
                       'Created social media posts during an internship|Assisted with marketing campaigns and events|Researched competitors and customer segments|Prepared marketing materials and presentations',
                       'Social media campaign plan for a local business|Marketing plan for a product launch (academic)|Customer survey and market research report',
                       'Digital marketing certification course|Google Analytics course|Content marketing training|Marketing internship'),
        early=_level('Campaign Execution|Lead Generation|Social Media Management|Content Creation|Campaign Reporting|CRM Updates',
                     'Planned and executed marketing campaigns and promotions|Generated leads through digital and offline channels|Created content and marketing collateral|Tracked campaign results and reported performance'),
        mid=_level('Performance Marketing|Marketing Automation|Brand Management|Event Management|Analytics & ROI|Vendor / Agency Coordination',
                   'Owned campaigns for a product line or channel|Managed paid campaigns and marketing budgets|Coordinated agencies, events and exhibitions|Analysed campaign ROI and optimised spend'),
        senior=_level('Marketing Strategy|Brand Strategy|Team Leadership|Budget Ownership|Go-to-Market Planning|Stakeholder Management',
                      'Led marketing planning for products or markets|Managed marketing budgets and teams where applicable|Built go-to-market plans with sales leadership|Directed brand and communication strategy'),
    ),
    _role(
        'Store Executive', 'nt', 'box', 'Stores & Inventory', 'Stock handling and records',
        'Store Executives handle the day-to-day running of the store. You receive and issue materials, update stock '
        'records and keep everything organised and traceable.',
        'Receive, inspect and store materials|Issue items against requisitions|'
        'Update stock registers and ERP records|Support stock-taking and audits',
        'Inventory Management|Stock Records|ERP / SAP Basics|MS Excel|GRN & Issue Notes|FIFO / FEFO|Material Handling|Accuracy',
        'Store Assistant|Store Executive|Senior Store Executive|Store Supervisor|Store Manager',
        fields=[
            ('Inventory management', 'Stock receiving|Stock issuing|Stock verification|Bin cards|Reorder levels'),
            ('Store documentation', 'GRN|Material issue notes|Delivery challans|Gate passes|Stock registers'),
            ('Systems', 'SAP MM|ERP|Tally|MS Excel|Barcode scanning'),
            ('Storage practices', 'FIFO / FEFO|Bin location system|5S|Material handling|Safe storage'),
            ('Audit & reconciliation', 'Physical stock count|Stock reconciliation|Audit support|Scrap management'),
            ('Coordination', 'Purchase coordination|Site / production coordination|Vendor deliveries'),
        ],
        recommended='SAP MM|Warehouse Management Systems|5S|Barcode / RFID|Inventory Analytics|Forklift Safety Awareness',
        certifications='SAP MM End User Certification|Warehouse Management Certification|Advanced Excel Certification|Certified Inventory Professional',
        focus='inventory management, stock records and material handling', knowledge='stores and inventory',
        goal='accurate, well-organised inventory',
        fresher=_level('Inventory Basics|MS Excel|Stock Record Keeping|Material Handling Awareness|Attention to Detail|Teamwork',
                       'Assisted in receiving and issuing materials during training|Updated stock registers and Excel trackers|Helped with physical stock counts|Organised materials using labelling and bins',
                       'Inventory tracking sheet with reorder alerts in Excel|ABC analysis of store items (academic)|Warehouse layout improvement study',
                       'Inventory and warehouse management course|SAP MM / ERP basics training|Advanced Excel course'),
        early=_level('Material Receipt & Issue|GRN Processing|Stock Records|ERP Entries|Stock Verification|Material Storage',
                     'Received and inspected incoming materials against POs|Issued materials against approved requisitions|Updated stock registers and ERP records|Supported physical stock counts and audits'),
        mid=_level('Inventory Control|Stock Reconciliation|Reorder Planning|Scrap & Surplus Management|Audit Coordination|Guiding Store Assistants',
                   'Controlled stock levels and reorder points|Reconciled physical and system stock|Managed scrap, returns and surplus materials|Coordinated stock audits and closed observations'),
        senior=_level('Store Operations Management|Inventory Optimisation|Team Supervision|Process Standardisation|Vendor & Purchase Coordination|Compliance',
                      'Managed store operations and staff|Reduced excess or slow-moving inventory|Standardised storage and documentation processes|Coordinated with purchase, finance and operations teams'),
    ),
    _role(
        'Store Supervisor', 'nt', 'clip', 'Stores & Inventory', 'Supervise stores and staff',
        'Store Supervisors oversee store staff and daily activity. You assign work, check stock accuracy, enforce safe '
        'storage and make sure materials reach the right place on time.',
        'Supervise store staff and daily tasks|Verify stock levels and resolve mismatches|'
        'Ensure safe storage and housekeeping|Coordinate with purchase and site teams',
        'Team Supervision|Inventory Control|Stock Auditing|ERP / SAP|Safety & Housekeeping|Planning|Coordination|Problem Solving',
        'Store Executive|Store Supervisor|Senior Supervisor|Store Manager|Stores Head',
        fields=[
            ('Team supervision', 'Shift planning|Work allocation|Staff training|Attendance monitoring'),
            ('Inventory control', 'Stock accuracy checks|Cycle counts|Reorder monitoring|Shortage / excess analysis'),
            ('Storage & safety', 'Safe storage|Housekeeping|5S|Fire safety|Material handling equipment'),
            ('Systems', 'SAP / ERP|MS Excel|Inventory reports'),
            ('Coordination', 'Purchase coordination|Production / site coordination|Logistics coordination'),
            ('Audits', 'Stock audits|Audit closure|Documentation control'),
        ],
        recommended='Lean Warehousing|SAP MM|Inventory Analytics|Team Leadership|Safety Management|Logistics Basics',
        certifications='Warehouse Management Certification|SAP MM End User Certification|Fire Safety Training Certificate|Six Sigma Yellow Belt',
        focus='inventory control, team coordination and safe storage practices', knowledge='stores operations',
        goal='efficient, safe and accurate store operations',
        fresher=_level('Inventory Basics|MS Excel|Teamwork|Communication|Safety Awareness|Problem-solving',
                       'Assisted store operations during an internship|Helped with stock counts and records|Supported housekeeping and 5S activities|Coordinated material requests',
                       '5S implementation plan for a store (academic)|Stock accuracy improvement study|Material flow mapping for a warehouse',
                       'Warehouse management course|SAP / ERP basics training|Safety and material handling training'),
        early=_level('Stock Control|Material Issue Supervision|ERP Updates|Housekeeping & 5S|Stock Counts|Shift Coordination',
                     'Supervised receipt, storage and issue of materials|Monitored stock records and ERP entries|Conducted cycle counts and resolved discrepancies|Maintained housekeeping and safe storage'),
        mid=_level('Team Supervision|Inventory Accuracy|Storage Planning|Audit Management|Process Improvement|Training Staff',
                   'Supervised store staff and daily task allocation|Improved inventory accuracy and resolved mismatches|Planned storage layout and space utilisation|Coordinated audits and closed observations'),
        senior=_level('Stores Management|Team Leadership|Inventory Optimisation|Safety Compliance|Cross-functional Coordination|Reporting to Management',
                      'Led store teams across shifts or locations|Optimised inventory levels and storage costs|Enforced safety and compliance standards|Reported inventory performance to management'),
    ),
    _role(
        'Store Manager', 'nt', 'box', 'Stores & Inventory', 'Run store operations and inventory',
        'Store Managers are responsible for the entire store. You manage stock levels, budgets and people, reduce '
        'wastage and make sure materials are always available when needed.',
        'Manage store operations and inventory budgets|Plan stock levels and reorder points|'
        'Lead and train store staff|Report on consumption, wastage and audits',
        'Inventory Planning|Warehouse Management|Team Leadership|ERP / SAP|Cost Control|Vendor Coordination|Audit & Compliance|Decision Making',
        'Store Supervisor|Assistant Store Manager|Store Manager|Senior Manager – Stores|Head of Supply Chain',
        fields=[
            ('Inventory planning', 'Demand planning|Reorder planning|Safety stock|ABC / XYZ analysis|Inventory budgets'),
            ('Warehouse management', 'Warehouse layout|Space utilisation|WMS|Logistics coordination|Material flow'),
            ('Team leadership', 'Team management|Training|Performance reviews|Manpower planning'),
            ('Cost control', 'Wastage reduction|Inventory carrying cost|Scrap disposal|Budget tracking'),
            ('Systems', 'SAP MM|ERP|Power BI|MS Excel'),
            ('Compliance & audits', 'Statutory compliance|Internal audits|Stock audits|SOPs'),
        ],
        recommended='Demand Planning|WMS|Power BI|Lean Six Sigma|Logistics Management|Vendor Management',
        certifications='Certified Supply Chain Professional (CSCP)|SAP MM Certification|Warehouse Management Certification|Six Sigma Green Belt',
        focus='inventory planning, warehouse operations and team management', knowledge='stores and supply chain',
        goal='cost-effective, reliable material availability',
        fresher=_level('Supply Chain Basics|Inventory Fundamentals|MS Excel|Communication|Teamwork|Planning Basics',
                       'Supported store and inventory activities during an internship|Analysed stock data under guidance|Prepared inventory reports|Studied store procedures and documentation',
                       'Inventory optimisation study using ABC analysis (academic)|Warehouse layout design project|Supply chain case study',
                       'Supply chain management course|Warehouse management training|SAP MM training'),
        early=_level('Store Operations|Inventory Records|Stock Audits|ERP / SAP|Vendor Coordination|Reporting',
                     'Handled store operations and inventory records|Coordinated with purchase and vendors on deliveries|Conducted stock audits and reconciliations|Prepared inventory and consumption reports'),
        mid=_level('Inventory Planning|Team Supervision|Cost Control|Warehouse Optimisation|Audit Management|Process Improvement',
                   'Planned stock levels and reorder points|Supervised store staff and operations|Reduced wastage and inventory carrying costs|Improved warehouse layout and material flow'),
        senior=_level('Store & Warehouse Leadership|Inventory Strategy|Budget Ownership|Team Leadership|Supply Chain Coordination|Compliance & Governance',
                      'Managed store operations, budgets and teams|Defined inventory planning policies|Partnered with procurement and operations on supply planning|Ensured audit readiness and compliance'),
    ),
    _role(
        'Purchase Executive', 'nt', 'cart', 'Procurement', 'Quotations, orders and follow-ups',
        'Purchase Executives handle buying support. You collect quotations, raise purchase orders, follow up with '
        'vendors and make sure deliveries arrive on time and as specified.',
        'Collect and compare vendor quotations|Raise purchase orders and track deliveries|'
        'Follow up with vendors and stores|Maintain vendor and PO records',
        'Vendor Sourcing|Quotation Comparison|Purchase Orders|Negotiation|ERP / SAP|MS Excel|Communication|Follow-up',
        'Purchase Trainee|Purchase Executive|Senior Purchase Executive|Purchase Manager|Head of Procurement',
        fields=[
            ('Sourcing', 'Vendor identification|Vendor registration|RFQ preparation|Supplier evaluation'),
            ('Quotation handling', 'Quotation comparison|Comparative statements|Price negotiation|Technical-commercial evaluation'),
            ('Purchase orders', 'PO creation|PO follow-up|Delivery tracking|Order amendments'),
            ('Systems', 'SAP MM|ERP|Tally|MS Excel'),
            ('Vendor coordination', 'Vendor follow-up|Delivery coordination|Payment coordination|Vendor records'),
            ('Purchase documentation', 'Purchase registers|GRN matching|Invoice verification|Contract basics'),
        ],
        recommended='SAP MM|Strategic Sourcing|Spend Analysis|Contract Management|Import / Export Basics|E-procurement Tools',
        certifications='SAP MM End User Certification|Certified Purchasing Professional|CIPS Level 4 Diploma|Negotiation Skills Certificate',
        focus='procurement processes, vendor communication and documentation', knowledge='procurement',
        goal='timely, cost-effective purchasing',
        fresher=_level('Procurement Basics|MS Excel|Communication|Negotiation Basics|Documentation|Follow-up',
                       'Assisted with collecting quotations during an internship|Prepared comparative statements in Excel|Followed up with vendors on deliveries|Maintained purchase records',
                       'Vendor evaluation model in Excel (academic)|Procurement process study for a company|Cost comparison of suppliers for a product',
                       'Procurement and purchasing course|SAP MM basics training|Negotiation skills training'),
        early=_level('RFQ & Quotation Comparison|Purchase Order Processing|Vendor Follow-up|Delivery Tracking|ERP / SAP Entries|Invoice Verification',
                     'Collected and compared vendor quotations|Raised purchase orders in ERP / SAP|Followed up on deliveries and resolved delays|Maintained vendor and PO records'),
        mid=_level('Vendor Development|Price Negotiation|Category Purchasing|Cost Savings Tracking|Supplier Performance|Contract Basics',
                   'Managed purchasing for assigned material categories|Negotiated prices and terms with vendors|Developed alternate vendors|Tracked supplier delivery and quality performance'),
        senior=_level('Procurement Planning|Strategic Sourcing|Team Supervision|Contract Negotiation|Spend Analysis|Compliance',
                      'Planned procurement for projects or categories|Led strategic sourcing and negotiations|Supervised purchase executives|Analysed spend and supplier risk'),
    ),
    _role(
        'Purchase Manager', 'nt', 'trend', 'Procurement', 'Procurement strategy and vendors',
        'Purchase Managers lead procurement. You build vendor relationships, negotiate contracts and costs, manage '
        'budgets and make sure the company buys the right quality at the right price.',
        'Plan procurement strategy and budgets|Negotiate rates and contracts with vendors|'
        'Lead the purchase team and approve POs|Evaluate vendor performance and risks',
        'Strategic Sourcing|Contract Negotiation|Vendor Management|Cost Analysis|Supply Chain Basics|ERP / SAP|Team Leadership|Decision Making',
        'Purchase Executive|Senior Executive|Purchase Manager|Senior Manager – Procurement|Head of Procurement',
        fields=[
            ('Strategic sourcing', 'Category management|Make-or-buy analysis|Global sourcing|Sourcing strategy'),
            ('Contracts & negotiation', 'Contract negotiation|Rate contracts|Terms & conditions|Price escalation clauses'),
            ('Vendor management', 'Vendor evaluation|Vendor development|Supplier audits|Supplier risk management'),
            ('Cost & budget', 'Cost analysis|Budget planning|Cost reduction|Spend analysis'),
            ('Team & process', 'Team leadership|Approval workflows|Procurement policies|Compliance'),
            ('Systems', 'SAP MM / Ariba|ERP|Power BI|MS Excel'),
        ],
        recommended='SAP Ariba|Contract Law Basics|Supplier Risk Management|Spend Analytics|Import / Export|Sustainable Procurement',
        certifications='CIPS Level 5 / 6|Certified Professional in Supply Management (CPSM)|Certified Supply Chain Professional (CSCP)|SAP Ariba Certification',
        focus='procurement, supply chain and negotiation', knowledge='procurement',
        goal='cost-effective, reliable supply',
        fresher=_level('Supply Chain Basics|Procurement Fundamentals|MS Excel|Negotiation Basics|Communication|Analytical Thinking',
                       'Supported procurement activities during an internship|Analysed vendor quotations under guidance|Prepared purchase reports|Studied purchase policies and documentation',
                       'Spend analysis case study (academic)|Supplier selection model using weighted criteria|Procurement strategy for a product category',
                       'Supply chain management course|Procurement and contract management training|SAP MM training'),
        early=_level('Purchase Processing|Vendor Coordination|Quotation Analysis|ERP / SAP|Delivery Follow-up|Negotiation',
                     'Processed purchase requisitions and orders|Compared quotations and recommended vendors|Coordinated with vendors on delivery and quality|Supported negotiations with senior buyers'),
        mid=_level('Category Management|Vendor Development|Contract Negotiation|Cost Reduction|Team Supervision|Supplier Performance',
                   'Managed procurement for major categories or projects|Negotiated contracts and rate agreements|Developed and evaluated vendors|Delivered cost savings through negotiation and alternate sourcing'),
        senior=_level('Procurement Strategy|Budget Ownership|Team Leadership|Supplier Risk Management|Policy & Compliance|Executive Negotiation',
                      'Led the procurement function or team|Defined sourcing strategy, policies and approval workflows|Owned procurement budgets and savings targets where applicable|Managed strategic supplier relationships and risks'),
    ),
]


# --------------------------------------------------------------------------- #
#  Assembly: defaults + admin overrides
# --------------------------------------------------------------------------- #

def summary_templates(role):
    """Editable summary templates for a role, keyed by level.

    Admin-provided templates win; otherwise the shared patterns are filled with
    the role's own focus words. Experienced templates keep [placeholders] for
    the candidate to replace — the builder never fills in experience for them.
    """
    custom = role.get('summary_templates') or {}
    focus = role.get('summary_focus') or {}
    values = {
        'title': role['title'],
        'focus': focus.get('focus') or 'the core skills of the role',
        'knowledge': focus.get('knowledge') or role['title'].lower(),
        'goal': focus.get('goal') or 'the goals of the team',
    }
    out = {}
    for level in LEVEL_KEYS:
        templates = _split(custom.get(level)) if custom.get(level) else []
        if not templates:
            templates = [p.format(**values) for p in SUMMARY_PATTERNS[level]]
        out[level] = templates
    return out


def _blank_level():
    return {'skills': [], 'responsibilities': [], 'projects': [], 'training': []}


def _apply_override(base, row):
    """Overlay a ``ResumeRoleTemplate`` row on a role dict (non-empty values win)."""
    role = dict(base) if base else {
        'slug': row.slug, 'title': row.title, 'category': row.category, 'icon': 'brief',
        'industry': '', 'subtitle': '', 'description': '', 'responsibilities': [],
        'required_skills': [], 'recommended_skills': [], 'career_path': [], 'certifications': [],
        'fields': [], 'levels': {k: _blank_level() for k in LEVEL_KEYS},
        'summary_focus': {}, 'experience_label': 'Professional Experience',
    }
    for attr in ('title', 'category', 'icon', 'industry', 'subtitle', 'description', 'experience_label'):
        value = (getattr(row, attr, '') or '').strip()
        if value:
            role[attr] = value
    for attr in ('responsibilities', 'required_skills', 'recommended_skills', 'career_path', 'certifications'):
        values = [line.strip() for line in (getattr(row, attr, '') or '').splitlines() if line.strip()]
        if values:
            role[attr] = values
    if isinstance(row.role_fields, list) and row.role_fields:
        fields = []
        for i, item in enumerate(row.role_fields):
            if isinstance(item, dict) and item.get('label'):
                fields.append({
                    'key': str(item.get('key') or slugify(item['label'])[:40] or f'field-{i}'),
                    'label': str(item['label']),
                    'options': _split(item.get('options') or []),
                })
        if fields:
            role['fields'] = fields
    if isinstance(row.level_suggestions, dict) and row.level_suggestions:
        levels = {k: dict(v) for k, v in (role.get('levels') or {}).items()}
        for level in LEVEL_KEYS:
            data = row.level_suggestions.get(level)
            if isinstance(data, dict):
                merged = dict(levels.get(level) or _blank_level())
                for key in ('skills', 'responsibilities', 'projects', 'training'):
                    if data.get(key):
                        merged[key] = _split(data[key])
                levels[level] = merged
        role['levels'] = levels
    if isinstance(row.summary_templates, dict) and row.summary_templates:
        role['summary_templates'] = row.summary_templates
    role['display_order'] = row.display_order
    return role


def get_roles():
    """All active roles: built-in defaults with admin overrides and additions.

    Never raises: if the override table is unavailable (e.g. before migrating),
    the built-in roles are returned unchanged.
    """
    roles = {r['slug']: dict(r) for r in BUILTIN_ROLES}
    order = {r['slug']: i * 10 for i, r in enumerate(BUILTIN_ROLES)}
    try:
        from django.db import transaction
        from .models import ResumeRoleTemplate
        with transaction.atomic():  # a savepoint, so a failure never breaks an outer transaction
            rows = list(ResumeRoleTemplate.objects.all())
    except Exception:  # table missing / DB unavailable — fall back to defaults
        rows = []
    for row in rows:
        if not row.is_active:
            roles.pop(row.slug, None)
            continue
        roles[row.slug] = _apply_override(roles.get(row.slug), row)
        if row.display_order:
            order[row.slug] = row.display_order
        else:
            order.setdefault(row.slug, 10_000)
    result = []
    for role in sorted(roles.values(), key=lambda r: (order.get(r['slug'], 10_000), r['title'])):
        role = dict(role)
        role['category_label'] = CATEGORY_LABELS.get(role['category'], role['category'])
        role['summaries'] = summary_templates(role)
        role.pop('summary_templates', None)
        role.pop('display_order', None)
        result.append(role)
    return result


def get_role(slug):
    for role in get_roles():
        if role['slug'] == slug:
            return role
    return None


CARD_KEYS = ('slug', 'title', 'category', 'category_label', 'icon', 'industry', 'subtitle', 'description',
             'responsibilities', 'required_skills', 'career_path')


def client_payload(full=False):
    """What the landing-page builder needs, as one JSON-safe dict.

    The page embeds the light version (role cards and the role overview); the
    form fields, level suggestions and summary templates of a role are fetched
    from the roles API when that role is opened, which keeps the page small.
    """
    roles = get_roles()
    if not full:
        roles = [{k: r.get(k) for k in CARD_KEYS} for r in roles]
    return {
        'roles': roles,
        'levels': [{'key': k, 'label': LEVEL_LABELS[k]} for k in LEVEL_KEYS],
        'level_common': LEVEL_COMMON,
        'categories': CATEGORY_LABELS,
        'sections': DEFAULT_SECTIONS,
    }
