"""
Management command: seed_jobs
Seeds job postings extracted from job_photos/ directory into the database.
Creates system employer profiles for each unique company (idempotent).
Now features rich, professional job descriptions and detailed requirements.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from jobs_app.models import EmployerProfile, JobPosting


# --- ALL JOBS EXTRACTED FROM 51 PHOTOS ---------------------------------------
# Format: (company_name, industry, location, title, description, requirements,
#          skills, job_type, experience, salary_min, salary_max, openings)
SEEDED_JOBS = [
    # -- Royal International Staffing -----------------------------------------
    (
        "Royal International Staffing", "Staffing & Recruitment", "Surat, Gujarat",
        "HR Supervisor - Site",
        """We are seeking an experienced and dynamic HR Supervisor to lead site-level human resources operations for our industrial clients across Surat. The ideal candidate will be responsible for end-to-end recruitment, onboarding, employee engagement, and compliance. You will collaborate with department heads to fulfill manpower requirements through campus drives, job fairs, and mass hiring campaigns. This is a high-impact role that demands both strategic thinking and hands-on execution. You will also manage attendance, payroll coordination, and grievance redressal to ensure smooth HR functioning on the shop floor.""",
        """• Bachelor's degree in Human Resources, Business Administration, or a related field (MBA preferred).
• 3-5 years of proven HR experience with at least 1 year in a supervisory or leadership role.
• Demonstrated experience in mass hiring, campus recruitment, and managing high-volume recruitment pipelines.
• Strong knowledge of labor laws, compliance regulations, and factory HR practices.
• Excellent interpersonal, communication, and conflict-resolution skills.
• Proficiency in MS Office (Excel, Word, PowerPoint) and HRMS software.
• Candidates with experience in industrial/manufacturing sector will be given preference.""",
        "Recruitment, Staffing, Campus Hiring, Mass Hiring, HR Operations, Communication",
        "full_time", "3-5", 25000, 35000, 1
    ),
    (
        "Royal International Staffing", "Staffing & Recruitment", "Surat, Gujarat",
        "Machine Operator (Extruder)",
        """Royal International Staffing is urgently hiring Machine Operators (Extruder) for our manufacturing clients in the PVC/XLPE cable industry in Surat. As a Machine Operator, you will be responsible for operating, monitoring, and maintaining extrusion machines to ensure continuous and quality production output. You will work in a shift-based environment and are expected to adhere strictly to safety protocols and production standards. Candidates with hands-on experience in cable manufacturing or polymer extrusion will be prioritized for immediate joining.""",
        """• ITI or Diploma in Mechanical, Electrical, or a relevant engineering trade.
• 1-3 years of hands-on experience in machine operation, preferably in extrusion or cable manufacturing.
• Working knowledge of PVC/XLPE cable extrusion processes and related machinery.
• Understanding of quality control measures and production standards.
• Ability to read and interpret technical drawings or machine manuals.
• Willingness to work in rotational shifts (day/night).
• Physical fitness to work in a manufacturing environment.
• Basic knowledge of machine maintenance and troubleshooting.""",
        "Machine Operation, Extrusion, PVC, XLPE, Manufacturing, Safety",
        "full_time", "1-2", 20000, 26000, 5
    ),
    (
        "Royal International Staffing", "Staffing & Recruitment", "Pandesara, Surat",
        "Back Office Executive",
        """We are looking for a detail-oriented and organized Back Office Executive to join our client's operations team in Pandesara, Surat. The primary responsibilities include maintaining accurate sales records, entering data into the company's CRM/ERP system, coordinating with clients and the sales team for order processing, and generating daily MIS reports. The role requires someone who can manage multiple tasks simultaneously with speed and precision. You will be a critical link between the front-end sales team and backend operations, ensuring seamless information flow and documentation accuracy.""",
        """• Graduate in Commerce, Business Administration, or any relevant discipline.
• 1-2 years of prior experience in back office, data entry, or administrative support roles.
• Proficiency in MS Office Suite, especially MS Excel (VLOOKUP, Pivot Tables) and MS Word.
• Experience with CRM/ERP systems is a strong plus.
• Strong attention to detail with excellent data accuracy and speed.
• Good written and verbal communication skills in English and Gujarati/Hindi.
• Ability to work independently and manage deadlines effectively.""",
        "MS Office, Data Entry, Customer Coordination, Sales Records, Administration",
        "full_time", "1-2", 15000, 20000, 3
    ),
    (
        "Royal International Staffing", "Staffing & Recruitment", "Sachin, Surat",
        "Helper & Machine Operator",
        """Royal International Staffing is immediately hiring Helpers and Machine Operators for our manufacturing client in the Sachin Industrial Area, Surat. As a production helper, you will assist senior operators in setting up and running production machinery, loading raw materials, performing basic quality checks, and maintaining cleanliness on the shop floor. This role is ideal for freshers or candidates with limited experience who wish to build a career in the manufacturing sector. Training will be provided to suitable candidates.""",
        """• Minimum 10th Standard (SSC) pass or ITI certificate is preferred.
• 0-2 years of experience in a manufacturing or factory environment; freshers are welcome.
• Basic understanding of machine operations and factory safety norms.
• Physical fitness and ability to handle manual tasks in a production setting.
• Willingness to work in rotating shifts including night shifts.
• Residing in or around Sachin, Surat is preferred for easy commute.
• Must be disciplined, punctual, and team-oriented.""",
        "Machine Operation, Factory Work, Production, Safety",
        "full_time", "fresher", 18000, 20000, 10
    ),
    (
        "Royal International Staffing", "Engineering & Infrastructure", "Pune / Sangli / Kolhapur",
        "Inspection Engineer - Rotary Equipment",
        """We are recruiting qualified Inspection Engineers (Rotary Equipment) for our clients in the engineering and petrochemical sectors across Pune, Sangli, and Kolhapur. The selected candidate will be responsible for conducting detailed in-service and pre-commissioning inspections of rotating mechanical equipment such as compressors, turbines, pumps, and agitators. You will apply a range of non-destructive testing techniques-VT, PT, MT, UT, RT-to ensure equipment integrity, reliability, and compliance with national and international standards. Your findings will be documented in comprehensive inspection reports for review by clients and regulatory authorities.""",
        """• B.E./B.Tech in Mechanical Engineering from a recognized university.
• ASNT Level II certification in at least two NDT methods (VT, PT, MT, UT, or RT) is mandatory.
• 3-8 years of post-qualification experience in mechanical inspection, specifically on rotating equipment.
• Familiarity with international inspection standards such as API 510, API 670, and ASME codes.
• Ability to read and interpret engineering drawings, P&IDs, and equipment data sheets.
• Experience with inspection in petrochemical, fertilizer, or power plant industries is highly preferred.
• Excellent technical report writing skills in English.""",
        "Mechanical Inspection, ASNT Level II, NDT, VT, PT, MT, UT, RT, Rotary Equipment",
        "full_time", "3-5", None, None, 2
    ),
    (
        "Royal International Staffing", "Engineering & Infrastructure", "Pune / Sangli / Kolhapur",
        "Inspection Engineer - Static Equipment",
        """Royal International Staffing is urgently seeking Inspection Engineers specializing in static equipment for clients in the process and petrochemical industries across Maharashtra. The role involves in-service inspection of static equipment including pressure vessels, heat exchangers, storage tanks, and piping systems. You will plan and execute inspection schedules, identify corrosion, cracks, or structural damage using NDT techniques, recommend appropriate repair strategies, and ensure that all equipment meets safety and compliance requirements. This is a critical safety role that demands a high level of technical expertise and professional judgment.""",
        """• B.E./B.Tech in Mechanical Engineering; candidates with a Diploma and extensive relevant experience will also be considered.
• Mandatory ASNT Level II certification (minimum two methods: UT and MT/PT).
• 3-8 years of experience in static equipment inspection in oil & gas, petrochemical, or fertilizer plants.
• Sound knowledge of inspection codes: ASME Section VIII (pressure vessels), API 653 (storage tanks), API 510 (piping).
• Proficiency in preparing Inspection Plans, Risk-Based Inspection (RBI) assessments, and technical reports.
• Familiarity with corrosion mechanisms and material degradation in process environments.
• Strong analytical skills and meticulous attention to safety and quality.""",
        "Mechanical Inspection, ASNT Level II, NDT, Pressure Vessels, Static Equipment, Piping",
        "full_time", "3-5", None, None, 2
    ),
    (
        "Royal International Staffing", "Engineering & Infrastructure", "Sachin, Gujarat",
        "Safety Officer",
        """We are looking for a dedicated and certified Safety Officer for our industrial client in the Sachin GIDC area of Gujarat. The Safety Officer will be responsible for developing, implementing, and enforcing health, safety, and environmental (HSE) policies across the plant. You will conduct risk assessments, investigate accidents and near-misses, organize safety training programs for workers, coordinate fire mock drills, and ensure compliance with all local and national safety regulations. You will serve as the primary point of contact for safety audits by external bodies and government inspectors. A proactive approach to hazard identification and mitigation is essential.""",
        """• Diploma in Industrial Safety (Government-recognized) is mandatory; B.E./B.Tech with safety certification is preferred.
• PDIS (Post Diploma in Industrial Safety) from the Gujarat Government is highly desirable.
• 5-7 years of experience in Environment, Health & Safety (EHS) management in an industrial setting.
• Thorough knowledge of Indian factory safety laws, Fire Safety Act, and EPR (Extended Producer Responsibility) norms.
• Hands-on experience with accident investigation, HIRA (Hazard Identification and Risk Assessment), and JSA (Job Safety Analysis).
• Strong communication, training facilitation, and documentation skills.
• NEBOSH IGC certificate will be an added advantage.""",
        "Compliance, EPR, Accident Safety, Fire Hydrant System, EHS Training, Safety Management",
        "full_time", "5-8", 50000, 70000, 2
    ),
    (
        "Royal International Staffing", "Engineering & Infrastructure", "Jamnagar, Gujarat",
        "Site Safety Officer",
        """Royal International Staffing is hiring a qualified Site Safety Officer for an active construction project in Jamnagar, Gujarat. The site involves large-scale civil and structural construction, and the safety officer will play a pivotal role in creating a zero-accident work environment. Responsibilities include conducting daily toolbox talks, performing site safety inspections, enforcing the use of Personal Protective Equipment (PPE), coordinating with subcontractors on safety compliance, and reporting safety metrics to the project management team. You will also be responsible for managing emergency response procedures and maintaining all safety documentation and records.""",
        """• B.E./B.Tech or Diploma in Civil/Mechanical Engineering with a specialization in Industrial Safety.
• NEBOSH IGC or ADIS (Advanced Diploma in Industrial Safety) certification is mandatory.
• 3-5 years of experience in site safety specifically for construction, infrastructure, or industrial projects.
• In-depth knowledge of construction safety norms, IS codes, and OISD standards.
• Experience with Fire Safety systems, scaffolding safety, and excavation safety.
• Familiarity with MS Office for report preparation and safety dashboards.
• Strong leadership skills to manage and enforce safety culture among workers and supervisors.""",
        "Safety Management, NEBOSH, ADIS, EHS, Construction Safety, Fire Safety, Compliance",
        "full_time", "3-5", 40000, 60000, 3
    ),
    (
        "Royal International Staffing", "Oil & Gas", "Saudi Arabia (KSA)",
        "Welding Inspector",
        """An exciting opportunity exists for experienced Welding Inspectors to join a major Oil & Gas construction project in the Kingdom of Saudi Arabia (KSA). As a Welding Inspector, you will oversee all welding activities on the project to ensure conformance with project specifications, welding procedures (WPS/PQR), and international codes such as ASME B31.3, ASME IX, and API 1104. Responsibilities include conducting visual inspections, reviewing radiographic test (RT) and PWHT reports, monitoring welder qualification tests, and issuing non-conformance reports (NCRs) when necessary. This is a high-compensation role with an accommodation and travel allowance package included.""",
        """• B.Tech or Diploma in Mechanical Engineering from a recognized institution.
• CSWIP 3.1 (Welding Inspector) certification is absolutely mandatory; BGAS Grade 2 is a strong plus.
• Minimum 8 years of post-qualification experience with at least 3-4 years of dedicated welding inspection experience in Oil & Gas construction projects.
• Strong knowledge of welding processes: SMAW, GTAW, GMAW, SAW, FCAW.
• Expertise in interpreting RT, UT, and other NDT reports; ASNT Level II in UT or RT preferred.
• Familiarity with international standards: ASME Sec. VIII, ASME IX, ASME B31.3, AWS D1.1, and API 1104.
• Willingness to relocate to Saudi Arabia on a contract basis.
• Good command of written and spoken English.""",
        "CSWIP 3.1, Welding Inspection, NDT, PWHT, ASME B31.3, API 1104, ASME IX, Oil & Gas",
        "contract", "8+", 150000, 165000, 15
    ),
    (
        "Royal International Staffing", "Oil & Gas", "Saudi Arabia",
        "Piping Inspector / Piping Engineer",
        """Royal International Staffing is on an immediate hiring drive for Piping Inspectors and Piping Engineers to be deployed on a prestigious Oil & Gas construction project in Saudi Arabia. The selected candidates will be responsible for inspecting and verifying piping fabrication, erection, and testing activities in accordance with Aramco standards and international codes. Duties include reviewing shop and field weld records, witnessing hydrotesting, punch-listing deficiencies, and coordinating with QA/QC teams and client representatives. This position offers a highly competitive salary with an attractive expat package.""",
        """• B.Tech or Diploma in Mechanical Engineering (Pipe Design/Piping Engineering preferred).
• 7-10 years of experience in piping inspection or piping engineering on Oil & Gas construction or brownfield projects.
• Strong knowledge of piping codes: ASME B31.3 (Process Piping) and ASME B31.4/B31.8.
• Familiarity with welding inspection (CSWIP or AWS CWI is an advantage).
• Experience with Aramco projects and CBT (Computer-Based Test) pre-qualification is highly preferred.
• Ability to read and interpret piping isometrics, P&IDs, and line lists.
• Proficiency in generating and reviewing punch lists and NCRs.
• Willingness to work in Saudi Arabia on a long-term contract basis.""",
        "Piping Inspection, ASME B31.3, API 1104, ASME IX, Aramco Standards, Oil & Gas, Welding Quality",
        "contract", "8+", 140000, 150000, 15
    ),
    (
        "Royal Staffing", "Manufacturing", "Katargam, Surat",
        "Laser Cutting Assistant",
        """Royal Staffing is hiring Laser Cutting Assistants for our diamond processing client in Katargam, Surat. This role involves assisting machine operators in running laser cutting machines used for precision diamond processing. Responsibilities include loading rough diamond material, monitoring machine operations under supervision, performing basic quality checks on cut output, and maintaining cleanliness and safety around the machine area. Free accommodation is provided for outstation female candidates. This is an excellent entry-level opportunity for women candidates looking to build a career in precision manufacturing.""",
        """• Minimum 10th Standard (SSC) pass; ITI certificate in any relevant trade is preferred.
• 0-1 year of experience in machine operation or manufacturing; freshers are actively encouraged to apply.
• Only female candidates are eligible for this position (as per client requirement).
• Basic understanding of machine safety procedures and a willingness to learn laser operation.
• Comfortable working in a well-ventilated, clean-room manufacturing environment.
• Willingness to work an 8-hour standard shift.
• Residence in Surat or willingness to relocate (free accommodation provided for outstation candidates).""",
        "Laser Cutting, Diamond Industry, Machine Operation, Quality Control",
        "full_time", "fresher", 15000, 20000, 100
    ),
    (
        "Royal Staffing", "Engineering & Infrastructure", "Kurnool, Andhra Pradesh",
        "Project Engineer",
        """Royal Staffing is on an urgent lookout for a Project Engineer for an electrical construction project in Kurnool, Andhra Pradesh. The candidate will be responsible for overseeing the day-to-day execution of electrical MEP works on a construction site, ensuring that activities are completed on time, within budget, and in compliance with engineering drawings and specifications. Key responsibilities include coordinating with subcontractors, managing material procurement and billing, preparing daily progress reports, resolving on-site technical issues, and liaising with the client's engineering team during inspections and handovers.""",
        """• B.Tech or Diploma in Electrical Engineering from a recognized institution.
• Up to 5 years of post-qualification experience in electrical construction site execution.
• Practical knowledge of MEP (Mechanical, Electrical, and Plumbing) systems in building or infrastructure projects.
• Proficiency in reading and interpreting electrical drawings, single-line diagrams, and load schedules.
• Experience in billing, BOQ preparation, and vendor coordination.
• Familiarity with IS codes for electrical installations.
• Strong interpersonal and team management skills.
• Candidates with experience on residential or commercial construction projects are preferred.""",
        "Electrical Engineering, MEP, Construction Site, Billing, Project Execution",
        "full_time", "3-5", 45000, 55000, 2
    ),
    (
        "Royal Staffing", "Engineering & Infrastructure", "Kurnool, Andhra Pradesh",
        "Project Manager - Electrical",
        """Royal Staffing is urgently hiring a seasoned Project Manager with a strong background in electrical construction for a large-scale project in Kurnool, Andhra Pradesh. As Project Manager, you will take complete ownership of the electrical construction project from mobilization through final handover to the client. This includes planning and scheduling, resource management, budget control, sub-contractor coordination, quality assurance, and maintaining a strong relationship with the client. You will lead a team of engineers, supervisors, and technicians and ensure that the project milestones are achieved without compromise on quality or safety.""",
        """• B.Tech or Diploma in Electrical Engineering; MBA or a PMP certification will be an added advantage.
• Up to 10 years of experience in electrical construction with at least 3 years in a project management role.
• Proven track record of successfully delivering electrical construction projects end-to-end.
• In-depth knowledge of MEP systems, contract management, and project scheduling (MS Project or Primavera).
• Strong leadership, stakeholder management, and client communication skills.
• Ability to manage multi-disciplinary teams and sub-contractors on a construction site.
• Knowledge of CPWD, ECBC, and relevant IS standards for electrical works.""",
        "Electrical Construction, Project Management, MEP, Site Management, Client Handover",
        "full_time", "8+", 70000, 80000, 1
    ),
    # -- Unique Digital Outreach -----------------------------------------------
    (
        "Unique Digital Outreach", "Sales & Marketing", "Gurgaon",
        "Inside Sales Executive",
        """Unique Digital Outreach, a fast-growing digital marketing and B2B solutions company, is looking for energetic Inside Sales Executives to drive revenue growth through structured outbound and inbound sales activities. You will be responsible for prospecting leads, nurturing relationships through calls and emails, maintaining the CRM pipeline, presenting product demos, and closing deals. This is a target-driven role with an attractive incentive structure. You will work closely with the marketing team to follow up on campaign-generated leads and with the accounts team for smooth onboarding of new clients.""",
        """• Bachelor's degree in Business, Marketing, or a related field.
• 1-3 years of experience in inside sales, telemarketing, or business development, preferably in a B2B environment.
• Excellent verbal and written communication skills in English and Hindi.
• Proficiency with CRM tools such as Salesforce, Zoho CRM, or HubSpot.
• Strong lead generation skills including cold calling, email campaigns, and LinkedIn outreach.
• Self-motivated, target-oriented, and comfortable working in a fast-paced sales environment.
• Prior experience in digital marketing, SaaS, or IT services sales is a significant advantage.""",
        "Sales, Communication, CRM, Lead Generation, Cold Calling, Inside Sales",
        "full_time", "1-2", None, None, 3
    ),
    (
        "Unique Digital Outreach", "Sales & Marketing", "Gurgaon",
        "Key Account Manager",
        """We are seeking a high-performing Key Account Manager (KAM) to manage and grow strategic client accounts for Unique Digital Outreach. As a KAM, you will serve as the primary point of contact for key enterprise clients, understanding their business goals, presenting tailored solutions, and ensuring their ongoing satisfaction and expansion. You will be responsible for upselling and cross-selling additional services, renewing contracts, and negotiating commercial terms. This role requires a blend of relationship management excellence and solution-oriented sales acumen.""",
        """• Bachelor's degree in Business, MBA preferred.
• 3-6 years of B2B sales experience with at least 2 years in a dedicated account management or KAM role.
• Demonstrated experience in managing high-value enterprise accounts and expanding revenue within them.
• Strong skills in consultative selling, negotiation, and stakeholder management up to the C-suite level.
• Proven ability to build long-term client relationships and achieve high client retention and NPS scores.
• Experience in the digital media, marketing technology, or SaaS industries is preferred.
• Strong analytical skills to track account health, pipeline metrics, and revenue forecasts.""",
        "Account Management, B2B Sales, Hunting, Client Retention, Upselling, Negotiation",
        "full_time", "3-5", None, None, 2
    ),
    (
        "Unique Digital Outreach", "Sales & Marketing", "Gurgaon",
        "Enterprise Sales Manager",
        """Unique Digital Outreach is expanding its enterprise client base and is looking for a driven Enterprise Sales Manager to lead on-ground and remote selling efforts. This is a high-visibility role where you will develop a territory-specific sales strategy, build a robust pipeline of large enterprise deals, lead product presentations and solution pitches, and close high-ticket contracts. You will manage a small team of field sales representatives and be responsible for their coaching, performance management, and weekly revenue reporting to senior leadership.""",
        """• MBA or a Post-Graduate degree in Marketing or Business Management.
• 5+ years of B2B sales experience with a minimum of 2-3 years in enterprise or field sales management.
• Proven track record of consistently achieving and exceeding annual sales targets (₹2 Cr+ preferred).
• Strong experience in on-ground field sales, territory management, and deal closing.
• Excellent leadership and mentoring skills to build and motivate a field sales team.
• Strong executive presence and the ability to present at the CXO level.
• Willingness to travel extensively across the assigned territory.""",
        "Enterprise Sales, Field Sales, B2B, Strategic Selling, Revenue Generation, Leadership",
        "full_time", "5-8", None, None, 2
    ),
    # -- BPO Convergence / Fornax ---------------------------------------------
    (
        "BPO Convergence", "BPO & Customer Service", "Hyderabad",
        "Customer Care Executive",
        """BPO Convergence (Fornax) is hiring Customer Care Executives for its rapidly expanding voice process operations in Hyderabad. As a Customer Care Executive, you will handle inbound customer queries related to products, services, billing, and technical issues, providing first-call resolution in a courteous and professional manner. You will update customer records in the CRM system, escalate complex issues to senior teams, and consistently meet quality and productivity targets. This is an excellent opportunity for freshers and experienced BPO professionals to grow their careers in a structured and supportive work environment with clear progression paths.""",
        """• Minimum 12th Standard (HSC) pass; a Bachelor's degree is preferred.
• Strong verbal communication skills in English and Hindi (regional language proficiency is a plus).
• 0-2 years of experience in a voice BPO, customer support, or call center environment; freshers with excellent communication skills are welcome.
• Basic computer proficiency including data entry and familiarity with CRM tools.
• Ability to handle high call volumes while maintaining a calm and professional demeanor.
• Flexible to work in rotational shifts including weekends.
• Quick learner with the ability to understand product knowledge and company processes.""",
        "Communication, English, Hindi, Customer Service, BPO, Problem Solving",
        "full_time", "fresher", 11000, 14000, 20
    ),
    # -- TechTiera Technologies ------------------------------------------------
    (
        "TechTiera Technologies", "IT & Software", "Hyderabad",
        "IT Recruiter",
        """TechTiera Technologies is seeking a passionate IT Recruiter to join its growing talent acquisition team in Hyderabad. You will be responsible for managing the full lifecycle of technical recruitment-from understanding job requirements with hiring managers to sourcing, screening, scheduling, coordinating technical interviews, and facilitating offer closures. You will build and maintain a robust pipeline of active and passive IT candidates using job portals (Naukri, LinkedIn), Boolean searches, and employee referrals. This is a role for someone who thrives in a fast-paced environment and has a genuine passion for connecting the right talent with the right opportunity.""",
        """• Bachelor's degree in Human Resources, Business Administration, or Information Technology.
• 1-3 years of hands-on IT recruitment experience, either in an RPO, staffing firm, or in-house talent team.
• Proficient in sourcing candidates through Naukri, LinkedIn Recruiter, Monster, and other job boards.
• Strong ability to evaluate resumes, conduct technical HR screening interviews, and assess candidate fitment.
• Familiarity with common IT skill sets: Java, Python, .NET, Cloud, Data, DevOps, QA, etc.
• Experience with Applicant Tracking Systems (ATS) is a plus.
• Excellent negotiation, communication, and stakeholder management skills.""",
        "IT Recruitment, Sourcing, Screening, LinkedIn, Communication, ATS, HR",
        "full_time", "1-2", None, None, 3
    ),
    # -- SS Professional Services ---------------------------------------------
    (
        "SS Professional Services", "IT & Cloud", "Bangalore",
        "Azure Architect - Migration & Modernization",
        """SS Professional Services is looking for an elite Azure Architect with deep expertise in cloud migration and application modernization to lead transformative projects for its global enterprise clients. You will be responsible for designing and delivering end-to-end Azure architecture solutions that include cloud-native application development on AKS (Azure Kubernetes Service), Azure Container Apps, and serverless functions. You will guide infrastructure-as-code practices using Terraform, Bicep, and ARM templates, establish DevSecOps pipelines with Azure DevOps and GitHub Actions, and implement comprehensive observability using Azure Monitor and Application Insights. This role requires a visionary technologist capable of advising at the CTO level.""",
        """• 12+ years of overall IT experience with a minimum of 5 years specializing in Microsoft Azure cloud architecture.
• Azure Solutions Architect Expert certification (AZ-305) is mandatory; additional certifications (AZ-400, AZ-104) are highly valued.
• Deep, hands-on expertise with Azure services: AKS, Azure Container Apps, Azure Functions, App Services, and Logic Apps.
• Advanced proficiency in Infrastructure-as-Code (IaC) using Terraform, Bicep, and ARM templates.
• Expert-level knowledge of CI/CD pipeline design and implementation with Azure DevOps and GitHub Actions.
• Strong background in PowerShell and Bash scripting for cloud automation.
• Experience with DevSecOps practices: security scanning, compliance-as-code, and zero-trust architecture.
• Excellent client-facing and architectural decision-making communication skills.""",
        "Azure, Azure Architecture, Azure Migration, AKS, Azure Container Apps, Serverless Functions, Terraform, Bicep, ARM Templates, PowerShell, Bash, Azure DevOps, GitHub Actions, Azure Monitor, DevSecOps",
        "full_time", "8+", 3000000, 4000000, 1
    ),
    # -- RBL Bank -------------------------------------------------------------
    (
        "RBL Bank", "Banking & Finance", "Indiranagar, Bangalore",
        "Relationship Manager (RM)",
        """RBL Bank is conducting a walk-in drive for dynamic Relationship Managers at its Indiranagar, Bangalore branch. As a Relationship Manager, you will be responsible for building and maintaining strong relationships with retail and priority banking customers. Your role will include identifying customer financial needs, recommending appropriate banking products (savings accounts, FDs, loans, insurance, wealth management), achieving monthly sales targets, and ensuring high customer satisfaction and retention. You will also be responsible for onboarding new customers and supporting the branch in its overall business development goals.""",
        """• A Bachelor's degree in Finance, Commerce, or Business Administration; MBA is preferred.
• 1-3 years of experience in retail banking, financial sales, or relationship management.
• Excellent interpersonal and persuasion skills with a proven ability to build trust with customers.
• Sound knowledge of banking products: savings accounts, fixed deposits, home loans, personal loans, mutual funds, and insurance.
• Target-driven with a strong track record of achieving sales goals consistently.
• Good written and spoken English; proficiency in Kannada is a strong plus for local customer engagement.
• AMFI/IRDAI certification is preferred.""",
        "Relationship Management, Banking, Communication, Customer Service, Sales",
        "full_time", "1-2", None, None, 10
    ),
    (
        "RBL Bank", "Banking & Finance", "Indiranagar, Bangalore",
        "Operations Executive",
        """RBL Bank is hiring Operations Executives for its Indiranagar branch as part of a walk-in drive. This is a back-office role where you will handle essential banking operations including account opening, KYC verification, transaction processing, NEFT/RTGS/IMPS processing, and customer data management. You will be responsible for maintaining accuracy and compliance in all operational activities while providing internal support to the branch sales and relationship team. The role demands a meticulous professional who can work efficiently under time pressure and maintain the highest standards of data integrity and regulatory compliance.""",
        """• Graduate in Commerce, Banking, or Business Administration.
• 1-2 years of experience in bank operations, back-office processing, or financial services.
• Strong knowledge of core banking operations including account management and transaction processing.
• Proficiency in MS Office (Excel and Word) and experience with Core Banking Software (Finacle, Bancs, or equivalent).
• Exceptional attention to detail and accuracy in data entry and document handling.
• Good knowledge of RBI guidelines, AML/KYC norms, and banking compliance practices.
• Ability to work under tight deadlines with minimal supervision.""",
        "Banking Operations, Data Entry, Customer Service, MS Office, Communication",
        "full_time", "1-2", None, None, 10
    ),
    # -- Funfirst Global Skillers ---------------------------------------------
    (
        "Funfirst Global Skillers", "Education & Training", "Vikhroli, Mumbai",
        "Vocational Trainer",
        """Funfirst Global Skillers, a leading skill development organization under the Government of India's PMKVY scheme, is seeking passionate and qualified Vocational Trainers to deliver hands-on training in high-demand trade sectors. As a Vocational Trainer, you will design and deliver theory and practical training sessions in RAC (Refrigeration & Air Conditioning), Electric Vehicles (EV), Solar Energy, and/or Optical Fiber Installation trades. You will be responsible for preparing training materials, conducting assessments, mentoring trainees, maintaining batch attendance and progress records, and ensuring a high placement rate among your trainees upon program completion.""",
        """• A Diploma or Bachelor's degree in the relevant technical trade (Electrical, Mechanical, Electronics, or Renewable Energy).
• ITI certification in the relevant trade is mandatory; Master Trainer certification is a strong advantage.
• 2+ years of hands-on industry experience in the specific trade you will be training for.
• 1-2 years of prior experience in vocational training, technical education, or skill development programs.
• Strong ability to communicate complex technical concepts in a simple, engaging manner.
• Familiarity with NSDC/PMKVY curriculum and assessment standards is preferred.
• Dedication to improving trainees' employability and a passion for teaching.""",
        "Vocational Training, RAC, EV, Solar, Optical Fiber, Teaching, Communication",
        "full_time", "1-2", None, None, 5
    ),
    (
        "Funfirst Global Skillers", "Education & Training", "Vikhroli, Mumbai",
        "Placement Officer",
        """Funfirst Global Skillers is looking for a proactive and result-oriented Placement Officer to drive industry connect and placement activities for its trained students. As a Placement Officer, you will build and maintain relationships with industry partners, employers, and corporate HR teams to create employment opportunities for skill-trained youth. You will organize job fairs, campus placement drives, and mock interview sessions, facilitate resume building for trainees, and track placement outcomes. You will play a crucial role in ensuring that the organization meets its placement KPIs as mandated by government skill development programs.""",
        """• A Bachelor's degree in HR, Social Work, Business Management, or a related field.
• Target-oriented with a proven ability to deliver results in a goal-driven environment.
• 1-3 years of experience in placements, HR, career counseling, or corporate liaison roles.
• Strong professional networking skills and the ability to build lasting relationships with industry stakeholders.
• Excellent verbal and written communication skills in English, Hindi, and/or Marathi.
• Proficiency in MS Office and comfortable maintaining MIS/placement tracking databases.
• Passion for social impact and youth empowerment through skill development.""",
        "Placement, Networking, Communication, Target Oriented, Coordination",
        "full_time", "1-2", None, None, 3
    ),
    (
        "Funfirst Global Skillers", "Education & Training", "Vikhroli, Mumbai",
        "Mobiliser / Telecaller",
        """Funfirst Global Skillers is hiring Mobilisers and Telecallers to support the enrollment of candidates for its Government-funded skill development programs. The role involves identifying and contacting potential beneficiaries in target communities through phone calls, local outreach, and social media channels. You will explain the benefits of skill training programs, screen candidate eligibility, and facilitate the enrollment and documentation process. This is a highly impactful role as you will be directly enabling unemployed and underemployed youth to access free skill training and gainful employment.""",
        """• Minimum 12th Standard (HSC) pass; a Bachelor's degree is preferred.
• 0-1 year of experience in telecalling, field mobilization, or community outreach; freshers are welcome.
• Strong communication skills in Hindi and Marathi (regional language proficiency is essential for local outreach).
• Basic proficiency in English for documentation and email communication.
• Comfortable making a large volume of outbound calls daily and meeting mobilization targets.
• Empathy and a genuine desire to help youth access education and employment opportunities.
• Own a smartphone and have basic knowledge of social media platforms (WhatsApp, Facebook).""",
        "Telecalling, Mobilization, Communication, Outreach, Lead Generation",
        "full_time", "fresher", None, None, 5
    ),
    (
        "Funfirst Global Skillers", "Education & Training", "Mumbai/Thane",
        "AC Refrigeration / CCTV / Fitter - Apprentice",
        """Funfirst Global Skillers, in association with leading industry partners, is offering a One-Year Apprenticeship Program for candidates seeking a career in skilled trades. This program provides structured on-the-job training in high-demand sectors: Air Conditioning & Refrigeration, CCTV Installation & Maintenance, and Industrial/Domestic Fitting. Apprentices will earn a stipend during the training period and will be certified under the Apprentices Act upon successful completion. The program is designed to bridge the gap between ITI/10th-12th education and industry employment, offering clear pathways to permanent employment with partner companies.""",
        """• 10th Standard (SSC) or 12th Standard (HSC) pass; ITI pass-outs in relevant trades are strongly preferred.
• Must have passed out of education in 2023, 2024, or 2025 (recent pass-outs only, as per apprenticeship norms).
• Basic knowledge of electrical/mechanical concepts is an advantage but not mandatory.
• Eagerness to learn and commitment to completing the 1-year apprenticeship program.
• Physically fit and willing to undertake hands-on technical work.
• Residing in or around Mumbai or Thane is preferred.
• Must be between 18-25 years of age (as per Apprentices Act guidelines).""",
        "AC Refrigeration, CCTV, Fitting, ITI, Skill Development",
        "internship", "fresher", None, None, 50
    ),
    # -- GMR Group ------------------------------------------------------------
    (
        "GMR Group", "Aviation & Retail", "Vishakhapatnam International Airport",
        "Retail Sales Associate / CSA",
        """GMR Group is inviting applications for Retail Sales Associates and Customer Service Associates for its prestigious Duty Free and retail operations at Vishakhapatnam International Airport. The role involves providing a world-class shopping experience to domestic and international travelers, assisting customers with product selection, maintaining store displays, processing sales transactions, and upselling premium products across categories such as Fashion, Electronics, Fragrances, and Liquor. You will represent the GMR brand of service excellence and be the face of the airport's retail experience to thousands of travelers daily.""",
        """• Minimum 12th Standard (HSC) pass; a Graduate degree is preferred.
• Age below 28 years at the time of application.
• A minimum of 2 years of experience in Retail, Duty Free, Fashion, or Electronics sales.
• Exceptional customer service skills with a pleasant and professional demeanor.
• Good communication skills in English; knowledge of Telugu or Hindi is an advantage.
• Comfortable working in a 24/7 airport retail environment with rotational shifts.
• Well-groomed appearance with strong product knowledge and selling skills.
• Prior experience in duty-free or airport retail will be given highest preference.""",
        "Retail, Customer Service, Communication, Duty Free, Fashion, Electronics, Airport Retail",
        "full_time", "1-2", None, None, 5
    ),
    # -- Petrocon Engineers ----------------------------------------------------
    (
        "Petrocon Engineers & Consultants", "Engineering & Construction", "Mangalore",
        "Revit MEP Trainee",
        """Petrocon Engineers & Consultants, a reputed MEP consulting firm, is offering a paid 6-month Training Program for fresh Diploma/B.E./B.Tech graduates who wish to build a career in BIM-based MEP design. As a Revit MEP Trainee, you will receive comprehensive, hands-on training in Building Information Modeling (BIM) using Autodesk Revit. Training will cover HVAC, Plumbing, Electrical, and Firefighting system design and modeling. Trainees who demonstrate exceptional performance will be offered a full-time position with the company upon successful completion of the training period. A stipend will be provided throughout the training program.""",
        """• Diploma or B.E./B.Tech in Mechanical, Electrical, or Civil Engineering from a recognized institution.
• Candidates from Mangalore and nearby locations are strongly preferred to minimize commuting constraints.
• Basic understanding of MEP systems (HVAC, Electrical, Plumbing) and engineering drawing interpretation.
• Prior exposure to AutoCAD is an advantage; experience with Revit MEP or BIM tools is a definite plus.
• A genuine interest in pursuing a career in BIM-based MEP design and construction consultancy.
• Commitment to completing the full 6-month training program (mandatory; early exits will not be considered).
• Strong analytical and problem-solving attitude with attention to detail.""",
        "BIM, Revit MEP, MEP Engineering, AutoCAD, Mechanical Engineering",
        "internship", "fresher", None, None, 100
    ),
    # -- Millicon Consultants -------------------------------------------------
    (
        "Millicon Consultants", "Engineering & Construction", "Ghansoli, Navi Mumbai",
        "Civil Structural Draftsman",
        """Millicon Consultants, a specialized structural engineering consultancy, is seeking an experienced Civil Structural Draftsman to join its technical team in Navi Mumbai. You will be responsible for preparing detailed shop drawings, general arrangement (GA) drawings, and structural detailing drawings for RCC and steel structural projects in AutoCAD. You will work closely with structural engineers to translate design intent into precise, buildable drawings. The role demands a high degree of accuracy, familiarity with Indian structural detailing standards, and the ability to manage multiple drawing revisions while meeting project deadlines.""",
        """• Diploma in Civil Engineering (Diploma candidates only; B.E./B.Tech applicants will not be shortlisted as per client requirement).
• 2-8 years of hands-on experience in structural drafting specifically using AutoCAD (not STAAD or ETABS).
• Strong proficiency in AutoCAD 2D for preparing RCC structural drawings (beams, columns, slabs, foundations) and steel structural drawings.
• Knowledge of Indian standards (IS 456, IS 800) for structural detailing.
• Ability to understand and interpret structural design outputs and engineer's sketches.
• Experience with GA drawings and preparation of Bar Bending Schedules (BBS) is a strong advantage.
• Willingness to work on a contract basis for the project duration.""",
        "AutoCAD, RCC, Steel Structural, Civil Drawings, GA Drawings, Structural Detailing, Drafting",
        "contract", "3-5", None, None, 1
    ),
    # -- BASE Education --------------------------------------------------------
    (
        "BASE Education", "Education & Training", "Kanakapura, Bangalore",
        "Chemistry Faculty",
        """BASE Education, one of South India's most respected competitive examination coaching institutes, is seeking a highly experienced and dedicated Chemistry Faculty member for its center in Kanakapura, Bangalore. The selected faculty will teach Chemistry for KCET, JEE, and NEET aspirants. Responsibilities include delivering conceptual lectures, designing MCQ test papers, conducting remedial sessions for weak students, and mentoring students for competitive exam success. Selection will be based entirely on a live demo lecture performance. The institute values result-oriented faculty who can inspire students and drive exceptional academic outcomes.""",
        """• Post-Graduate degree (M.Sc.) in Chemistry from a recognized university; Ph.D. or B.Ed. is an additional advantage.
• Minimum 5 years of experience teaching Chemistry specifically for competitive exams (KCET, JEE Main/Advanced, NEET) at a reputed coaching institute.
• Deep subject matter expertise with the ability to explain complex organic, inorganic, and physical chemistry concepts with clarity and precision.
• Proven track record of producing state/national rank holders or consistent top-scoring students.
• Excellent pedagogical skills with experience in MCQ-pattern teaching and assessment.
• Strong command of English and Kannada for effective communication with students and parents.
• Male candidates are preferred as per the specific client requirement for this center.""",
        "Chemistry, Teaching, KCET, MCQ Preparation, Communication, Faculty",
        "full_time", "5-8", None, None, 1
    ),
    # -- Fidelity National Financial -------------------------------------------
    (
        "Fidelity National Financial", "IT & Software", "India",
        ".NET Developer (4-6 Years)",
        """Fidelity National Financial (FNF), a certified Great Place to Work and Fortune 500 company, is hiring mid-level .NET Developers to join its India development center. As a .NET Developer, you will design, develop, and maintain enterprise-grade web applications and APIs that serve millions of users in the US real estate and financial services market. You will work in an Agile Scrum environment, participate in sprint planning, code reviews, and collaborate closely with US-based product owners and technical architects. This role offers world-class learning opportunities, a great work culture, and competitive compensation.""",
        """• Bachelor's degree (B.E./B.Tech/MCA) in Computer Science or a related field.
• 4-6 years of professional experience in .NET development using .NET Core and C#.
• Hands-on experience with Blazor (WebAssembly or Server-side) for building modern web UIs.
• Proficiency in building and consuming RESTful Web APIs using ASP.NET Core.
• Strong database skills with Microsoft SQL Server (stored procedures, query optimization, Entity Framework).
• Familiarity with Azure cloud services (App Services, Azure SQL, Azure DevOps) is preferred.
• Understanding of SOLID principles, design patterns, and clean code practices.
• Experience with unit testing frameworks (xUnit, NUnit) and CI/CD pipelines.""",
        ".NET Core, Blazor, C#, Web API, SQL, .NET Developer",
        "full_time", "3-5", None, None, 3
    ),
    (
        "Fidelity National Financial", "IT & Software", "India",
        ".NET Developer - Senior (8-11 Years)",
        """Fidelity National Financial is looking for Senior .NET Developers with significant experience to lead the design and delivery of complex, high-performance enterprise applications. In this role, you will architect and implement microservices-based solutions using .NET Core, build responsive Angular frontends, drive technical decisions in the team, and mentor junior developers. You will work on mission-critical applications serving the US financial and title insurance market, ensuring that solutions are scalable, resilient, and maintainable. This position offers leadership opportunities and direct collaboration with global technology leaders.""",
        """• B.E./B.Tech/MCA in Computer Science or equivalent; a Master's degree is a plus.
• 8-11 years of hands-on .NET development experience with strong expertise in .NET Core and C#.
• Extensive experience designing and building Microservices architectures using .NET Core.
• Proficiency in Angular (version 12+) for building complex, single-page enterprise applications.
• Expert-level knowledge of Microsoft SQL Server and database design for enterprise applications.
• Experience with Docker, Kubernetes, and Azure cloud deployment is highly desired.
• Strong understanding of distributed system patterns, API gateway design, and event-driven architecture.
• Demonstrated experience in technical leadership, code reviews, and mentoring junior engineers.""",
        ".NET Core, Angular, Microservices, C#, SQL, Web API",
        "full_time", "8+", None, None, 2
    ),
    (
        "Fidelity National Financial", "IT & Software", "India",
        "Data Engineer",
        """Fidelity National Financial is seeking a talented Data Engineer to join its data platform team. You will be responsible for designing, building, and optimizing scalable data pipelines and ETL workflows that process large volumes of financial transactions and real estate data from multiple source systems. You will work with Azure Data Factory (ADF), Azure Databricks (ADB), and PySpark to ingest, transform, and load data into the enterprise data lake and warehouse. You will also contribute to creating analytical reports and dashboards using PowerBI, enabling business intelligence across the organization.""",
        """• Bachelor's degree (B.E./B.Tech) in Computer Science, Information Systems, or a related field.
• 4+ years of data engineering experience with a strong focus on Azure data platform services.
• Proficient in Azure Data Factory (ADF) for orchestrating complex data pipeline workflows.
• Hands-on expertise with Azure Databricks (ADB) and Apache Spark/PySpark for large-scale data processing.
• Strong SQL skills for data transformation, quality validation, and complex query writing.
• Proficiency in Python for scripting, data manipulation, and automation tasks.
• Experience creating and managing dashboards and reports in Microsoft Power BI.
• Familiarity with data warehousing concepts (Star/Snowflake schema), Delta Lake, and data governance.""",
        "ADF, ADB, PySpark, SQL, Python, PowerBI, Data Engineering, ETL",
        "full_time", "3-5", None, None, 2
    ),
    (
        "Fidelity National Financial", "IT & Software", "India",
        "Senior Tech Lead - Full Stack",
        """Fidelity National Financial is looking for an accomplished Senior Tech Lead to drive the full stack engineering roadmap for its India technology division. In this high-impact leadership role, you will be responsible for architectural design decisions, technology scouting, development best practices enforcement, and hands-on delivery of complex full stack features using .NET Core (backend) and Angular (frontend). You will lead and mentor a team of 8-12 engineers, conduct design and code reviews, facilitate sprint ceremonies as a technical scrum master, and be the primary liaison between business stakeholders and the engineering team.""",
        """• B.E./B.Tech in Computer Science; a Master's degree or relevant certifications are a plus.
• 14-17 years of total IT experience with at least 5 years in a tech lead or architecture role.
• Expert-level proficiency in both .NET Core (C# backend) and Angular (TypeScript frontend).
• Demonstrated experience leading full stack development teams of 8+ engineers in an Agile environment.
• Strong architectural background in Microservices, API design, cloud-native applications, and performance optimization.
• Deep expertise in Azure cloud platform, DevOps practices, and CI/CD pipeline management.
• Exceptional communication, stakeholder management, and technical decision-making skills.
• Experience in the financial services or insurance domain is a strong plus.""",
        ".NET Core, Angular, Full Stack, Technical Leadership, Architecture, C#",
        "full_time", "8+", None, None, 1
    ),
    (
        "Fidelity National Financial", "IT & Software", "India",
        "Technical Architect",
        """Fidelity National Financial is hiring a visionary Technical Architect to define and own the long-term technology architecture for its enterprise platforms. You will collaborate with business leaders, product managers, and engineering directors to translate business strategy into scalable, robust, and cost-effective architectural solutions. Your responsibilities will include creating architecture blueprints and solution design documents, evaluating and selecting emerging technologies, establishing cloud architecture standards on Azure, designing for resilience and high availability using patterns such as event sourcing, CQRS, and Saga, and governing architecture compliance across delivery teams.""",
        """• B.E./B.Tech in Computer Science; a Master's degree in Computer Science or an MBA in Technology Management is preferred.
• 15+ years of progressive IT experience with at least 5 years in a solutions or enterprise architect role.
• Expert-level knowledge of Microsoft Azure platform (AZ-305 certification mandatory).
• Proven track record of designing large-scale, distributed enterprise applications using .NET, Azure Functions, and Cosmos DB.
• Deep expertise in Azure DevOps for end-to-end DevSecOps pipeline management.
• Strong knowledge of cloud-native architecture patterns: microservices, event-driven architecture, CQRS, API gateway patterns.
• Experience with cloud cost optimization, capacity planning, and FinOps practices.
• Exceptional executive communication skills for presenting architectural decisions to C-suite stakeholders.""",
        ".NET, Azure, Azure Functions, Cosmos DB, Azure DevOps, Architecture, Cloud",
        "full_time", "8+", None, None, 1
    ),
    (
        "Fidelity National Financial", "IT & Governance", "India",
        "IT Governance Analyst",
        """Fidelity National Financial is seeking a meticulous IT Governance Analyst to strengthen its technology risk, compliance, and governance frameworks. In this role, you will manage and maintain the IT governance policy framework, conduct periodic risk assessments, assist with IT audits (internal and external), analyze audit data to identify control gaps, and report findings to the CISO and technology leadership. You will work closely with IT, Legal, and Compliance teams to ensure that technology processes align with regulatory requirements including SOX, GDPR, and NIST frameworks. This role is ideal for a professional who combines technical understanding with a sharp eye for risk and compliance.""",
        """• Bachelor's degree in Information Technology, Computer Science, or a related field; CISA, CRISC, or CGEIT certification is strongly preferred.
• 5-8 years of experience in IT governance, IT risk management, or IT audit within a regulated financial services environment.
• Thorough knowledge of governance frameworks: COBIT, ISO 27001, NIST Cybersecurity Framework, and SOX compliance.
• Strong proficiency in audit data analysis using Excel, SQL, or GRC tools.
• Ability to understand and evaluate complex IT environments and translate technical risks into business risk language.
• Experience conducting IT risk assessments, control testing, and remediation tracking.
• Excellent report writing and stakeholder presentation skills.""",
        "Data Governance, IT Risk Management, Audit Data Analysis, Compliance, IT Governance",
        "full_time", "5-8", None, None, 1
    ),
    # -- Hexaware -------------------------------------------------------------
    (
        "Hexaware Technologies", "IT & Software", "Any Hexaware Location, India",
        "Senior Software Engineer / Technical Specialist",
        """Hexaware Technologies, a global technology and business process services company, invites applications from experienced technology professionals to join its accelerating Digital, Cloud & Infrastructure practice. The selected candidate will work on a portfolio of global client engagements, developing and delivering high-performance, scalable software solutions. Your primary stack will include .NET Core for backend services, MongoDB for document database management, Azure for cloud deployments, and SQL for relational data management. You will be embedded in a high-performance Agile team, contribute to architecture discussions, and participate in knowledge sharing through internal tech talks and communities of practice.""",
        """• B.E./B.Tech/MCA in Computer Science or a related engineering discipline.
• 7-10 years of professional experience in enterprise software engineering.
• Strong expertise in .NET Core and C# for developing robust backend services and APIs.
• Hands-on experience with MongoDB (schema design, indexing, aggregation pipelines, replica sets).
• Proficient in Microsoft SQL Server for complex queries, stored procedures, and performance tuning.
• Good understanding of Azure cloud platform services (App Services, Azure SQL, Blob Storage, Service Bus).
• Experience with unit and integration testing, code reviews, and Git-based branching strategies.
• Ability to work in a globally distributed team across multiple time zones.""",
        "MongoDB, SQL, Azure, .NET Core, .NET, Senior Software Engineer",
        "full_time", "5-8", None, None, 5
    ),
    # -- JSW Energy ------------------------------------------------------------
    (
        "JSW Energy (Utkal) Ltd", "Energy & Power", "Jharsuguda, Odisha",
        "Finance & Accounts Manager",
        """JSW Energy (Utkal) Ltd, part of the prestigious JSW Group, is looking for a Finance & Accounts Manager for its thermal power plant in Jharsuguda, Odisha. The Manager will lead the plant's finance and accounts function, responsible for financial planning, budgeting, cost control, statutory compliance, taxation, and audit management. Key responsibilities include preparation of monthly P&L and balance sheet, management of accounts payable/receivable, coordination with internal and external auditors, ensuring GST, TDS, and income tax compliance, and reporting to the Corporate Finance team. This is a leadership role with direct visibility to senior management.""",
        """• Chartered Accountant (CA) qualification is mandatory; ICWA/CMA qualification will also be considered.
• 4-6 years of post-qualification experience in Finance & Accounts, preferably in a manufacturing, power, or heavy industry environment.
• Strong expertise in financial reporting, management accounting, and statutory compliance (GST, TDS, Income Tax, Companies Act).
• Experience coordinating statutory and internal audit processes.
• Proficiency in ERP systems (SAP FI/CO preferred) and advanced MS Excel.
• Excellent analytical, problem-solving, and financial modeling skills.
• Strong communication and reporting skills for interaction with corporate leadership and auditors.""",
        "Finance, Accounts, CA, Financial Reporting, Auditing, Taxation, MS Excel",
        "full_time", "3-5", None, None, 1
    ),
    (
        "JSW Energy (Utkal) Ltd", "Energy & Power", "Jharsuguda, Odisha",
        "Land and Liaison Officer",
        """JSW Energy (Utkal) Ltd is seeking an experienced Land and Liaison Officer to manage its land-related functions and government liaison activities for ongoing power sector projects in Jharsuguda, Odisha. The officer will be responsible for land acquisition activities, maintaining comprehensive land records and documentation, coordinating with revenue authorities, district administration, and government departments to facilitate statutory approvals and clearances. The role also involves managing community relations, resolving land disputes amicably, and ensuring that all land-related regulatory requirements are complied with efficiently and ethically.""",
        """• Any Bachelor's degree (Law, Social Science, or relevant field preferred).
• 5-8 years of hands-on experience in land acquisition, government liaison, or revenue management roles, specifically in the power, mining, or infrastructure sector.
• Strong working relationships with Revenue Officers, Tehsil/District Administration, and State Government officials.
• Thorough understanding of land acquisition laws, LARR Act 2013, and relevant Odisha state regulations.
• Excellent negotiation and conflict resolution skills for managing land disputes and community relations.
• Fluency in Odia language is mandatory; proficiency in Hindi and English is necessary for official documentation.
• Willingness to travel extensively within Jharsuguda and surrounding districts.""",
        "Land Acquisition, Liaison, Government Relations, Communication, Coordination",
        "full_time", "5-8", None, None, 1
    ),
    # -- Steadfast ------------------------------------------------------------
    (
        "Steadfast", "Engineering & Construction", "Cochin",
        "CAD Draughtsman",
        """Steadfast Engineering is looking for a skilled CAD Draughtsman to join its MEP design team in Cochin. The successful candidate will prepare detailed shop drawings, as-built drawings, and coordination drawings for MEP systems including HVAC, Plumbing, Firefighting, and Electrical systems on large-scale commercial and infrastructure construction projects. You will collaborate with design engineers to convert design concepts into precise, construction-ready CAD drawings, and will be responsible for maintaining drawing registers, managing revisions, and adhering to client drawing standards and submittal schedules.""",
        """• B.Tech or Diploma in Mechanical, Electrical, or Civil Engineering.
• 1-5 years of dedicated experience in CAD drafting for MEP systems in construction projects.
• Advanced proficiency in AutoCAD 2D (mandatory); knowledge of AutoCAD MEP or Revit is an advantage.
• Practical knowledge of HVAC systems, plumbing layouts, firefighting systems, and electrical distribution.
• Ability to read and interpret MEP design drawings, specifications, and coordination drawings.
• Familiarity with client drawing standards, submittal processes, and revision management.
• Candidates with Gulf/UAE project experience will be given preference.
• Strong time management skills with the ability to deliver multiple drawing packages under tight deadlines.""",
        "AutoCAD, MEP, HVAC, Civil Drawings, Plumbing, Firefighting, Electrical, 2D Drafting",
        "full_time", "1-2", None, None, 3
    ),
    # -- ImagInnovate ---------------------------------------------------------
    (
        "ImagInnovate", "IT & Software", "Vishakhapatnam, India",
        "React UI Developer",
        """ImagInnovate is a product-focused technology company building innovative digital solutions for healthcare, education, and retail sectors. We are looking for an experienced React UI Developer to join our tight-knit, high-performing engineering team in Vizag. You will be responsible for architecting and developing complex, responsive user interfaces using React.js, managing application state with Redux/Context API, integrating with RESTful and GraphQL APIs, and writing clean, well-tested code. You will also contribute to our DevOps culture by participating in containerization with Docker and supporting Jenkins-based CI/CD pipelines. This is a work-from-office role in Vishakhapatnam.""",
        """• B.E./B.Tech in Computer Science or a related engineering discipline.
• 5-8 years of professional experience in frontend/UI development with a minimum of 3 years focused on React.js.
• Expert-level proficiency in React.js ecosystem including hooks, Redux, Context API, and React Router.
• Strong proficiency in JavaScript (ES6+), TypeScript, HTML5, and CSS3 (SASS/LESS).
• Demonstrated experience building and consuming REST APIs and/or GraphQL APIs.
• Experience with Docker for containerization and Jenkins for CI/CD pipeline management.
• Knowledge of Angular is a plus (for cross-framework collaboration).
• Mandatory: Must be willing to work from office in Vishakhapatnam (no remote option available).""",
        "React.js, Angular, JavaScript, REST APIs, SASS, LESS, Docker, Jenkins, UI Development",
        "full_time", "5-8", None, None, 2
    ),
    # -- Mergen ServiceNow ----------------------------------------------------
    (
        "Mergen Corp", "IT & Software", "Whitefield-ITPL, Bangalore",
        "Selenium Test Engineer",
        """Mergen Corp's ServiceNow Center of Excellence (CoE) is hiring experienced Selenium Test Engineers to build and maintain a robust test automation ecosystem for its enterprise ServiceNow platform implementations. The role involves designing and developing automation test frameworks using Selenium WebDriver, creating and executing test scripts for web application regression testing, integrating automated tests into the CI/CD pipeline using Jenkins and Azure DevOps, conducting API testing using Postman and Rest Assured, and providing detailed test reports and defect logs. This is a 4-days-from-office role based in Whitefield, Bangalore.""",
        """• B.E./B.Tech in Computer Science, Information Technology, or a related field.
• 5+ years of professional experience in software test automation with Selenium WebDriver being a core skill (non-negotiable).
• Strong expertise in designing automation frameworks (Page Object Model, Hybrid, Data-Driven) using Java, Python, or C#.
• Proficiency in TestNG, JUnit, and Cucumber (BDD) for structured test execution and reporting.
• Hands-on experience with API testing tools: Postman and Rest Assured.
• Experience integrating Selenium tests into CI/CD pipelines using Jenkins and/or Azure DevOps.
• Knowledge of Agile/Scrum methodologies and working in 2-week sprint cycles.
• Experience with ServiceNow platform testing (UI and API) is a significant advantage but not mandatory.""",
        "Selenium, Selenium WebDriver, TestNG, JUnit, Cucumber, Java, Python, C#, JavaScript, CI/CD, Jenkins, Azure DevOps, API Testing, Postman, Rest Assured, Agile, Scrum",
        "full_time", "5-8", None, None, 2
    ),
    # -- Equitas Small Finance Bank --------------------------------------------
    (
        "Equitas Small Finance Bank", "Banking & Finance", "Kasturinagar / TC Palya, Bangalore",
        "Premium Acquisition Manager",
        """Equitas Small Finance Bank is conducting a walk-in drive for Premium Acquisition Managers at its Kasturinagar and TC Palya branches in Bangalore. In this role, you will be responsible for acquiring high-net-worth individual (HNI) and affluent customer segments for Equitas' premium Current Account and Fixed Deposit products. You will build a strong pipeline of HNI prospects through networking, referrals, and local market scouting, present Equitas' product suite compellingly, complete KYC and onboarding formalities, and achieve monthly acquisition targets. This is a high-earning role with a strong incentive structure tied to your performance.""",
        """• A Bachelor's degree in Finance, Commerce, or Business Administration.
• 2+ years of experience in banking, financial services sales, or wealth management.
• Demonstrated ability to acquire and onboard HNI or affluent customer segments.
• Strong knowledge of banking products: Current Accounts, Fixed Deposits, CASA, and wealth management solutions.
• Sound understanding of KYC norms, AML regulations, and customer onboarding processes.
• Excellent communication, networking, and consultative selling skills.
• Self-driven with a high degree of personal accountability for target achievement.
• Existing network of HNI contacts in Bangalore is a significant advantage.""",
        "Banking, KYC, Current Accounts, HNI Acquisition, Finance, Customer Onboarding, Sales",
        "full_time", "1-2", None, None, 10
    ),
    # -- L&T Construction -----------------------------------------------------
    (
        "L&T Construction", "Engineering & Construction", "Chennai",
        "Structural Design Engineer",
        """L&T Construction - Buildings & Factories (B&F) division is seeking experienced Structural Design Engineers to join its Design Engineering Group in Chennai. The role involves the structural design and analysis of a diverse portfolio of large-scale projects including high-rise residential buildings, commercial complexes, industrial warehouses, and public infrastructure facilities. You will utilize industry-leading structural analysis software, interpret geotechnical reports, design reinforced concrete and structural steel systems, prepare design basis reports, and ensure all designs comply with applicable IS and international codes. This is a high-growth role within one of India's largest and most prestigious engineering organizations.""",
        """• Post-Graduate degree (M.E./M.Tech) in Structural Engineering or Civil Engineering with a structural specialization from a reputed institution.
• 3-15 years of structural design experience across residential, commercial, or industrial projects.
• Advanced proficiency in structural analysis software such as ETABS, STAAD.Pro, and SAP2000.
• Strong knowledge of Indian design codes: IS 456 (RCC), IS 800 (Steel), IS 1893 (Earthquake), and IS 875 (Wind and Live Load).
• Experience with post-tensioned (PT) slabs, transfer slabs, and deep basement design is a significant advantage.
• Proficiency in AutoCAD for preparing structural drawings and details.
• Strong technical report writing skills and ability to interface with clients, architects, and site teams.""",
        "Structural Design, Civil Engineering, AutoCAD, Structural Analysis, Engineering Design",
        "full_time", "3-5", None, None, 5
    ),
    (
        "L&T Construction", "Engineering & Construction", "Chennai",
        "HVAC Design Engineer",
        """L&T Construction invites experienced HVAC Design Engineers to join its MEP Design Group for the Buildings & Factories division in Chennai. You will be involved in the end-to-end HVAC design for large-scale, technically complex projects including Data Centers, Pharmaceutical Plants, Airports, and Commercial Towers. Responsibilities include heat load calculations, HVAC system selection and sizing, energy performance simulation, duct and pipe sizing, preparation of design drawings, and coordination with architectural, electrical, and plumbing disciplines. You will work in a collaborative design environment using industry-standard design and BIM tools.""",
        """• Bachelor's or Master's degree in Mechanical Engineering.
• 3-15 years of HVAC design experience specifically in a consultancy or design office environment.
• Strong expertise in HVAC system design: VAV, VRF, Chilled Water Systems, AHUs, FCUs, and precision cooling for Data Centers.
• Proficiency in HVAC design and simulation software: HAP (Hourly Analysis Program), Carrier E20, or IDA ICE.
• Experience with ASHRAE standards, ECBC 2017 compliance, and energy efficiency analysis.
• Knowledge of Revit MEP or BIM tools for coordinated design is highly preferred.
• Experience designing HVAC for pharmaceutical cleanrooms, data centers, or airport terminal buildings is a strong differentiator.""",
        "HVAC, MEP, Mechanical Engineering, HVAC Design, Construction, Facilities Engineering",
        "full_time", "3-5", None, None, 5
    ),
    (
        "L&T Construction", "Engineering & Construction", "Chennai",
        "Electrical Design Engineer",
        """L&T Construction's Buildings & Factories division is seeking skilled Electrical Design Engineers to contribute to the electrical system design for landmark infrastructure projects. The selected engineer will be responsible for the design of HT/LT power distribution systems, lighting layouts, emergency power systems (DG sets and UPS), Extra Low Voltage (ELV) systems (CCTV, BMS, PA, Fire Alarm), and ICT (structured cabling) systems. You will prepare single-line diagrams (SLDs), cable schedules, load calculations, and equipment selection reports, ensuring compliance with NBC, CPWD, and relevant IEC/IS standards.""",
        """• Bachelor's or Master's degree in Electrical Engineering from a recognized institution.
• 3-15 years of electrical design experience, preferably in an MEP consultancy or EPC company.
• Strong knowledge of HT/LT power system design, electrical load flow analysis, and short-circuit calculations.
• Proficiency in electrical design software such as DIALux (lighting), ETAP (power systems), and AutoCAD Electrical.
• In-depth knowledge of ELV systems: BMS, CCTV, Fire Alarm, and structured cabling (ICT).
• Familiarity with NBC 2016, CPWD specifications, and relevant IEC/IEEE/IS standards for electrical installations.
• Experience with Revit MEP for BIM-based electrical design coordination is an advantage.""",
        "Electrical Design, ELV, ICT, MEP, Power Systems, Electrical Engineering",
        "full_time", "3-5", None, None, 5
    ),
    (
        "L&T Construction", "Engineering & Construction", "Hyderabad / Saudi Arabia",
        "MEP Engineer / Manager",
        """L&T Construction is building next-generation Data Centres for a global technology client and is seeking MEP Engineers and Managers to join its site execution team in Hyderabad (India) and Saudi Arabia. As a MEP Engineer/Manager, you will oversee the site execution, coordination, and quality assurance of all MEP systems including HVAC, ELV, Plumbing, Firefighting (FPS), and Public Health Engineering (PHE). You will manage MEP sub-contractors, review and approve MEP shop drawings, coordinate with the structural and civil team for sleeves and openings, and ensure that MEP work is executed per design specifications, QA/QC plans, and client standards.""",
        """• Diploma, Bachelor's, or Master's degree in Mechanical, Electrical, or Civil Engineering.
• 5-15 years of MEP construction experience on large-scale commercial, industrial, or mission-critical projects.
• Demonstrated expertise in at least two of the following disciplines: HVAC, ELV, Plumbing, Firefighting, or PHE.
• Strong site coordination and sub-contractor management skills.
• Proficiency in reviewing and approving MEP shop drawings and method statements.
• Experience with QA/QC documentation, inspection and test plans (ITPs), and punch list management.
• Experience with Data Centre MEP execution is highly preferred.
• Willingness to relocate internationally (Saudi Arabia) for project-based assignments.""",
        "MEP, HVAC, ELV, PHE, FPS, Procurement, QA/QC, Construction Management, Project Management",
        "full_time", "5-8", None, None, 20
    ),
    # -- TCS ------------------------------------------------------------------
    (
        "Tata Consultancy Services", "IT & Software", "Vishakhapatnam",
        "Citizen Service Executive",
        """Tata Consultancy Services (TCS) is conducting a Walk-in Drive for Citizen Service Executives at the Visakhapatnam Passport Seva Kendra. Additional vacancies are also available in Hyderabad and Vijayawada Passport Seva Kendras. As a Citizen Service Executive, you will be the front-line representative of the TCS and Ministry of External Affairs collaboration, handling passport applications, verifying supporting documents, enrolling applicants for biometric data collection, addressing citizen queries professionally, and ensuring a smooth, courteous, and efficient passport services experience for all applicants. This is a high-visibility, citizen-centric government services role.""",
        """• A Bachelor's degree (any discipline) from a recognized university.
• Good communication skills in English and Telugu (mandatory for citizen interaction).
• 0-2 years of experience in customer service, data entry, or government service delivery roles; freshers with strong communication skills are welcome.
• Basic computer proficiency and fast, accurate data entry skills.
• Positive, patient, and professional attitude towards citizens/public from all walks of life.
• Familiarity with passport application procedures and MEA guidelines is an advantage.
• Candidates must NOT have appeared for a TCS interview in the last 6 months.
• Must be willing to work in shifts at the Passport Seva Kendra.""",
        "Customer Service, Communication, English, Government Services, Data Entry, Passport Services",
        "full_time", "fresher", None, None, 20
    ),
]


class Command(BaseCommand):
    help = 'Seeds job postings from job_photos/ directory into the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('[*] Seeding job postings from job_photos...'))

        # Create or get a system user for seeded employers
        system_user, user_created = User.objects.get_or_create(
            username='system_seeder',
            defaults={
                'email': 'system@bizengliish.com',
                'first_name': 'System',
                'last_name': 'Seeder',
                'is_active': True,
            }
        )
        if user_created:
            system_user.set_unusable_password()
            system_user.save()
            self.stdout.write(f'  [+] Created system user: system_seeder')

        # Build employer profiles per company
        employer_cache = {}

        total_created = 0
        total_updated = 0
        total_skipped = 0

        for job_data in SEEDED_JOBS:
            (
                company_name, industry, emp_location,
                title, description, requirements,
                skills, job_type, experience,
                salary_min, salary_max, openings
            ) = job_data

            # Get or create employer profile for this company
            if company_name not in employer_cache:
                # Each company gets its own dedicated User for the FK
                company_username = 'seed_' + company_name.lower().replace(' ', '_').replace('-', '_').replace('&', 'and')[:40]
                company_user, _ = User.objects.get_or_create(
                    username=company_username,
                    defaults={
                        'email': f'{company_username}@seeded.com',
                        'first_name': company_name[:30],
                        'is_active': False,
                    }
                )
                if _:
                    company_user.set_unusable_password()
                    company_user.save()

                employer, emp_created = EmployerProfile.objects.get_or_create(
                    user=company_user,
                    defaults={
                        'company_name': company_name,
                        'industry': industry,
                        'location': emp_location,
                        'company_size': '500+',
                        'description': f'Seeded employer profile for {company_name}.',
                        'company_website': '',
                    }
                )
                employer_cache[company_name] = employer
                if emp_created:
                    self.stdout.write(f'  [+] Created employer: {company_name}')
            else:
                employer = employer_cache[company_name]

            # Create or UPDATE job posting (idempotent by title + employer, updates description/requirements)
            job, created = JobPosting.objects.get_or_create(
                title=title,
                employer=employer,
                defaults={
                    'description': description.strip(),
                    'requirements': requirements.strip(),
                    'skills_required': skills,
                    'job_type': job_type,
                    'experience': experience,
                    'salary_min': salary_min,
                    'salary_max': salary_max,
                    'location': emp_location,
                    'openings': openings,
                    'status': 'active',
                    'is_seeded': True,
                }
            )

            if created:
                total_created += 1
                self.stdout.write(f'  [+] Created: [{company_name}] {title}')
            else:
                # Update description and requirements to reflect any improvements
                job.description = description.strip()
                job.requirements = requirements.strip()
                job.skills_required = skills
                job.salary_min = salary_min
                job.salary_max = salary_max
                job.openings = openings
                job.is_seeded = True
                job.save()
                total_updated += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Seeding complete! Created: {total_created} | Updated: {total_updated} | Skipped: {total_skipped}'
        ))
