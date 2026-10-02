"""
Management command: seed_it_jobs
Seeds 55+ IT-domain job postings across Web Dev, DevOps, Cloud, Data,
AI/ML, Cybersecurity, Mobile, QA, Database, Networking, and more.
Safe to re-run - already-existing titles are skipped.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from jobs_app.models import EmployerProfile, JobPosting

IT_JOBS = [
    # -- Web / Full-Stack Development -------------------------------------
    (
        "TechNova Solutions", "Information Technology", "Bangalore, Karnataka",
        "Full Stack Developer (React + Node.js)",
        """TechNova Solutions is looking for a talented Full Stack Developer to build and
maintain scalable web applications. You will work closely with the product and design
teams to develop feature-rich frontend UIs in React and robust backend APIs in Node.js.
You are expected to write clean, maintainable code, participate in code reviews, and
contribute to architectural decisions.""",
        """• 2-5 years of full-stack development experience.
• Strong proficiency in React.js (hooks, context API, Redux).
• Solid backend experience with Node.js and Express.js.
• Experience with RESTful API design and GraphQL.
• Proficiency with relational (PostgreSQL/MySQL) and non-relational (MongoDB) databases.
• Familiarity with Docker, CI/CD pipelines, and cloud platforms (AWS/GCP/Azure).
• Good understanding of HTML5, CSS3, and responsive design.
• Version control with Git; agile/scrum methodology experience preferred.""",
        "React.js, Node.js, Express.js, MongoDB, PostgreSQL, GraphQL, Docker, AWS, Git",
        "full_time", "2-5", 60000, 120000, 3
    ),
    (
        "InnoCode Labs", "Information Technology", "Hyderabad, Telangana",
        "Vue.js Frontend Developer",
        """InnoCode Labs is seeking a skilled Vue.js Frontend Developer to build intuitive,
high-performance user interfaces for our SaaS platform. You will work in an agile team,
translating Figma designs into polished, accessible components, integrating with REST
APIs, and optimizing frontend performance.""",
        """• 2-4 years of hands-on Vue.js (Vue 2 & Vue 3) development.
• Strong knowledge of Vuex/Pinia state management.
• Experience with TypeScript, Webpack, and Vite.
• Familiarity with Jest/Vitest for unit testing.
• Good understanding of CSS3, SCSS, and CSS-in-JS solutions.
• Experience consuming REST/GraphQL APIs.
• Knowledge of accessibility (WCAG) standards is a plus.
• Git version control; CI/CD pipeline experience preferred.""",
        "Vue.js, Vuex, TypeScript, JavaScript, SCSS, REST APIs, Jest, Git, Vite",
        "full_time", "2-4", 55000, 100000, 2
    ),
    (
        "CodeBridge Technologies", "Information Technology", "Pune, Maharashtra",
        "Django / Python Backend Developer",
        """CodeBridge Technologies requires an experienced Python/Django Developer to design
and implement backend services for our enterprise-grade web platform. Responsibilities
include developing REST APIs, database modeling, performance optimization, and
integrating third-party services. You will mentor junior developers and contribute to
system design decisions.""",
        """• 3-6 years of Python development with strong Django expertise.
• Experience with Django REST Framework (DRF) and JWT/OAuth authentication.
• Strong PostgreSQL/MySQL skills including query optimization and indexing.
• Experience with Celery, Redis for background task processing.
• Familiarity with Docker, Kubernetes, and AWS/GCP services.
• Understanding of software design patterns and SOLID principles.
• Experience with unit testing (pytest, unittest) and CI/CD pipelines.
• Git-based workflow and agile team experience.""",
        "Python, Django, DRF, PostgreSQL, Redis, Celery, Docker, AWS, REST APIs, pytest",
        "full_time", "3-6", 70000, 140000, 2
    ),
    (
        "WebSphere India", "Information Technology", "Mumbai, Maharashtra",
        "MERN Stack Developer",
        """WebSphere India is hiring a MERN Stack Developer to build scalable, real-time web
applications. You will work across the entire stack-from React-based SPAs to MongoDB-backed
Node.js APIs-and collaborate with cross-functional teams to deliver high-quality
software in an agile environment.""",
        """• 2-5 years of experience with the MERN stack (MongoDB, Express, React, Node.js).
• Proficiency in JavaScript (ES6+) and TypeScript.
• Experience with Socket.io for real-time features.
• Knowledge of JWT-based authentication and authorization.
• Familiarity with Docker, AWS EC2/S3, and Nginx.
• Experience with Redux Toolkit and React Query.
• Strong debugging and problem-solving skills.
• Knowledge of testing frameworks like Jest and Mocha.""",
        "MongoDB, Express.js, React.js, Node.js, JavaScript, TypeScript, Docker, JWT, Redux",
        "full_time", "2-5", 55000, 110000, 3
    ),
    (
        "PixelCraft Software", "Information Technology", "Chennai, Tamil Nadu",
        "WordPress / PHP Web Developer",
        """PixelCraft Software is looking for an experienced WordPress and PHP developer to
build custom themes, plugins, and WooCommerce solutions for our diverse client base.
You will manage the full development lifecycle-from requirement gathering to
deployment-while ensuring performance, security, and SEO best practices.""",
        """• 2-4 years of PHP and WordPress development experience.
• Strong skills in custom theme and plugin development.
• Experience with WooCommerce, ACF, and page builders (Elementor/Divi).
• Proficiency in MySQL database design and query optimization.
• Knowledge of RESTful API integration and webhooks.
• Understanding of web security best practices (OWASP).
• Familiarity with cPanel, Linux hosting environments.
• Basic knowledge of HTML5, CSS3, JavaScript, jQuery.""",
        "PHP, WordPress, WooCommerce, MySQL, JavaScript, jQuery, HTML5, CSS3, REST APIs",
        "full_time", "2-4", 35000, 70000, 2
    ),

    # -- Mobile Development --------------------------------------------------
    (
        "AppSprint Technologies", "Information Technology", "Bangalore, Karnataka",
        "Android Developer (Kotlin)",
        """AppSprint Technologies is seeking a skilled Android Developer with strong Kotlin
expertise. You will design and build advanced mobile applications, ensuring high
performance and responsiveness. You will collaborate with backend engineers to integrate
APIs, implement MVVM architecture, and ensure code quality through testing.""",
        """• 2-5 years of Android application development experience.
• Expert-level knowledge of Kotlin; Java is a plus.
• Strong understanding of MVVM, Clean Architecture, and SOLID principles.
• Experience with Jetpack libraries: Room, Navigation, ViewModel, LiveData, Compose.
• Familiarity with Retrofit, OkHttp for API integration.
• Experience with Firebase (Firestore, Auth, FCM).
• Published apps on Google Play Store preferred.
• Knowledge of unit testing (JUnit, Mockito) and CI/CD for mobile.""",
        "Kotlin, Android, Jetpack Compose, MVVM, Room, Retrofit, Firebase, Git, JUnit",
        "full_time", "2-5", 65000, 130000, 2
    ),
    (
        "MobileFirst India", "Information Technology", "Delhi NCR",
        "iOS Developer (Swift / SwiftUI)",
        """MobileFirst India is hiring a passionate iOS Developer to create beautiful,
high-performance iOS applications. You will work on both greenfield and legacy projects
using Swift and SwiftUI, integrating REST APIs, implementing Core Data, and ensuring
App Store submission compliance.""",
        """• 2-5 years of iOS app development experience.
• Strong proficiency in Swift and SwiftUI; Objective-C knowledge is a plus.
• Experience with UIKit and Auto Layout.
• Solid understanding of iOS design patterns (MVC, MVVM, VIPER).
• Experience with Core Data, Keychain, and local storage.
• Familiarity with Combine framework and async/await.
• Experience with CocoaPods, SPM, and Fastlane for CI/CD.
• Published apps on Apple App Store is preferred.""",
        "Swift, SwiftUI, UIKit, Core Data, REST APIs, Combine, Xcode, MVVM, Fastlane",
        "full_time", "2-5", 70000, 135000, 2
    ),
    (
        "CrossPlatform Labs", "Information Technology", "Hyderabad, Telangana",
        "React Native Mobile Developer",
        """CrossPlatform Labs needs a React Native Developer to build and maintain
cross-platform mobile apps for iOS and Android. You'll work on both UI and logic layers,
optimize JavaScript bundles, handle native module bridging when needed, and ensure
smooth integration with backend APIs.""",
        """• 2-5 years of React Native experience with production-grade apps.
• Proficiency in JavaScript and TypeScript.
• Experience with Redux or Zustand for state management.
• Familiarity with Native Modules, Expo, and react-navigation.
• Knowledge of REST API integration and offline-first strategies.
• Experience with push notifications (FCM, APNs).
• App Store / Play Store deployment experience.
• Debugging skills using Flipper, Reactotron, and Chrome DevTools.""",
        "React Native, JavaScript, TypeScript, Redux, Expo, Firebase, REST APIs, iOS, Android",
        "full_time", "2-5", 60000, 120000, 2
    ),
    (
        "FlutterWave India", "Information Technology", "Bangalore, Karnataka",
        "Flutter Developer",
        """FlutterWave India is seeking an experienced Flutter Developer to build natively
compiled mobile and web applications from a single codebase. You will work with the
product team to implement pixel-perfect UI designs, integrate Firebase and REST APIs,
and ensure excellent app performance across platforms.""",
        """• 2-4 years of Flutter/Dart development experience.
• Proficiency in Dart and Flutter SDK.
• Experience with state management (Bloc, Provider, Riverpod, GetX).
• Knowledge of Firebase integration (Auth, Firestore, Storage, FCM).
• Familiarity with RESTful API integration using Dio/http packages.
• Experience with platform channels for native features.
• Published apps on Google Play / App Store.
• Experience with CI/CD tools like Codemagic or Bitrise.""",
        "Flutter, Dart, Bloc, Firebase, REST APIs, Android, iOS, Riverpod, Codemagic",
        "full_time", "2-4", 60000, 115000, 3
    ),

    # -- DevOps / Cloud / Infrastructure ----------------------------------
    (
        "CloudOps India", "Information Technology", "Bangalore, Karnataka",
        "DevOps Engineer (AWS + Kubernetes)",
        """CloudOps India is looking for a hands-on DevOps Engineer to design, build, and
maintain our cloud infrastructure on AWS. You will manage Kubernetes clusters, build
CI/CD pipelines, implement infrastructure-as-code with Terraform, and collaborate with
development teams to enable fast, reliable software delivery.""",
        """• 3-6 years of DevOps / infrastructure engineering experience.
• Expert knowledge of AWS services: EC2, EKS, RDS, S3, CloudFront, Lambda.
• Hands-on experience with Kubernetes (EKS) and Helm charts.
• Proficiency in Terraform and CloudFormation for IaC.
• Experience with Jenkins, GitHub Actions, or GitLab CI/CD pipelines.
• Strong Linux system administration and shell scripting skills.
• Familiarity with monitoring tools: Prometheus, Grafana, CloudWatch.
• Experience with Docker and container orchestration.""",
        "AWS, Kubernetes, Docker, Terraform, Jenkins, GitHub Actions, Prometheus, Grafana, Linux, Helm",
        "full_time", "3-6", 80000, 160000, 2
    ),
    (
        "InfraScale Technologies", "Information Technology", "Pune, Maharashtra",
        "GCP Cloud Engineer",
        """InfraScale Technologies is hiring a GCP Cloud Engineer to manage and optimize our
Google Cloud Platform infrastructure. You will architect scalable cloud solutions, manage
GKE workloads, implement security best practices, and support development teams with
cloud-native tooling.""",
        """• 3-5 years of Google Cloud Platform experience.
• Proficiency with GKE, GCS, Cloud SQL, Pub/Sub, Cloud Run, BigQuery.
• Experience with Terraform or Deployment Manager for IaC.
• Knowledge of GCP IAM, VPC networking, and security policies.
• Experience with Cloud Build and Cloud Deploy for CI/CD.
• Familiarity with monitoring via Cloud Monitoring and Cloud Logging.
• GCP Associate Cloud Engineer or Professional certification preferred.
• Strong Python or Go scripting skills.""",
        "GCP, Kubernetes, GKE, Terraform, BigQuery, Cloud Run, Python, Docker, CI/CD",
        "full_time", "3-5", 75000, 150000, 2
    ),
    (
        "DeployX Solutions", "Information Technology", "Remote / Bangalore",
        "Site Reliability Engineer (SRE)",
        """DeployX Solutions is seeking an SRE to ensure reliability, performance, and
scalability of our production systems. You will work on reducing toil through automation,
defining SLIs/SLOs/SLAs, conducting post-incident reviews, and building resilient,
observable systems.""",
        """• 4-7 years of SRE or senior DevOps experience.
• Strong proficiency in Python, Go, or Shell scripting for automation.
• Deep experience with Kubernetes, Docker, and service meshes (Istio/Linkerd).
• Expert knowledge of observability: Prometheus, Grafana, ELK Stack, Jaeger.
• Experience with chaos engineering (Chaos Monkey, Gremlin).
• Strong understanding of distributed systems and CAP theorem.
• Experience with incident management tools (PagerDuty, OpsGenie).
• Excellent problem-solving and on-call incident response skills.""",
        "Python, Go, Kubernetes, Docker, Prometheus, Grafana, ELK, Istio, SRE, AWS, GCP",
        "full_time", "4-7", 100000, 200000, 1
    ),
    (
        "PipelinePro Technologies", "Information Technology", "Hyderabad, Telangana",
        "CI/CD & Build Engineer",
        """PipelinePro Technologies is looking for a Build & Release Engineer to manage and
optimize our software delivery pipelines. You will design and maintain CI/CD pipelines,
manage artifact repositories, automate testing gates, and ensure high-quality software
releases through robust automation.""",
        """• 3-5 years of experience in build, release, or DevOps engineering.
• Strong experience with Jenkins, GitHub Actions, GitLab CI, or Azure DevOps.
• Proficiency with Docker and containerized build environments.
• Experience with Nexus or Artifactory for artifact management.
• Knowledge of Gradle, Maven, or Make build systems.
• Familiarity with GitOps workflows and ArgoCD or FluxCD.
• Shell/Python scripting for automation.
• Experience with SAST/DAST tooling integration in pipelines.""",
        "Jenkins, GitHub Actions, Docker, Kubernetes, ArgoCD, Python, Nexus, GitLab CI",
        "full_time", "3-5", 70000, 130000, 2
    ),

    # -- Data Engineering / Analytics --------------------------------------
    (
        "DataFlow India", "Information Technology", "Bangalore, Karnataka",
        "Data Engineer (Spark / Databricks)",
        """DataFlow India is hiring a Data Engineer to design and build large-scale data
pipelines using Apache Spark and Databricks. You will work with petabyte-scale data,
implement ETL workflows, optimize Delta Lake tables, and support the Analytics and ML
teams with clean, reliable data.""",
        """• 3-6 years of data engineering experience.
• Strong PySpark / Scala expertise for large-scale data processing.
• Experience with Databricks (Workflows, Delta Live Tables, MLflow).
• Proficiency in SQL; experience with dbt for transformation.
• Knowledge of cloud storage: AWS S3, Azure Data Lake, GCS.
• Experience with orchestration tools: Apache Airflow or Prefect.
• Understanding of data quality frameworks and data governance.
• Familiarity with streaming: Kafka or Kinesis.""",
        "PySpark, Databricks, Delta Lake, SQL, Airflow, Kafka, Python, dbt, AWS S3",
        "full_time", "3-6", 80000, 160000, 2
    ),
    (
        "InsightFlow Analytics", "Information Technology", "Mumbai, Maharashtra",
        "Business Intelligence (BI) Developer",
        """InsightFlow Analytics is looking for a BI Developer to build comprehensive
dashboards, data models, and reports for business stakeholders. You will work with
data from multiple sources, design star/snowflake schema models, and deliver insights
through Power BI, Tableau, or Looker.""",
        """• 2-5 years of BI development experience.
• Advanced Power BI (DAX, Power Query, RLS, DirectQuery) or Tableau skills.
• Strong SQL and data modeling skills (star/snowflake schema, slowly changing dimensions).
• Experience with ETL/ELT pipelines: SSIS, Azure Data Factory, or Informatica.
• Knowledge of data warehousing concepts (Azure Synapse, Redshift, BigQuery, Snowflake).
• Ability to translate business requirements into technical data solutions.
• Experience with Azure Analysis Services or SSAS is a plus.
• Strong communication skills to present insights to non-technical stakeholders.""",
        "Power BI, DAX, SQL, Tableau, Azure Data Factory, Snowflake, ETL, Data Modeling",
        "full_time", "2-5", 60000, 120000, 2
    ),
    (
        "StreamAnalytics Co.", "Information Technology", "Hyderabad, Telangana",
        "Apache Kafka Data Streaming Engineer",
        """StreamAnalytics Co. is hiring a Data Streaming Engineer to design and operate
real-time data pipelines using Apache Kafka. You will build event-driven architectures,
implement stream processing with Kafka Streams or Apache Flink, and ensure reliability,
scalability, and fault tolerance of streaming infrastructure.""",
        """• 3-5 years of data engineering experience with focus on streaming.
• Expert knowledge of Apache Kafka (topics, partitions, consumer groups, Kafka Connect).
• Experience with Kafka Streams or Apache Flink for stream processing.
• Proficiency in Python or Java/Scala.
• Knowledge of schema registries (Avro, Protobuf, JSON Schema).
• Experience with cloud-managed Kafka: Confluent Cloud or AWS MSK.
• Strong understanding of exactly-once semantics and offset management.
• Familiarity with monitoring: Kafka JMX metrics, Prometheus, Grafana.""",
        "Kafka, Apache Flink, Python, Java, Avro, Confluent, AWS MSK, Prometheus, Spark",
        "full_time", "3-5", 80000, 150000, 2
    ),

    # -- AI / Machine Learning / Data Science ------------------------------
    (
        "NeuralNest India", "Information Technology", "Bangalore, Karnataka",
        "Machine Learning Engineer",
        """NeuralNest India is looking for an ML Engineer to design, develop, and deploy
machine learning models at production scale. You will work on the full ML lifecycle-from
data preprocessing and feature engineering to model training, evaluation, and serving
via REST APIs or batch pipelines-using modern MLOps practices.""",
        """• 3-6 years of machine learning engineering experience.
• Strong Python skills with expertise in scikit-learn, TensorFlow, or PyTorch.
• Experience with ML pipelines: MLflow, Kubeflow, or SageMaker.
• Proficiency in feature engineering, model evaluation, and A/B testing.
• Experience deploying models as REST APIs (FastAPI, Flask).
• Knowledge of distributed training and GPU optimization.
• Familiarity with experiment tracking and model versioning.
• Strong SQL and data manipulation skills (Pandas, NumPy).""",
        "Python, PyTorch, TensorFlow, scikit-learn, MLflow, FastAPI, Docker, AWS SageMaker, Pandas",
        "full_time", "3-6", 90000, 180000, 2
    ),
    (
        "AIVision Labs", "Information Technology", "Bangalore, Karnataka",
        "Computer Vision Engineer",
        """AIVision Labs is seeking an experienced Computer Vision Engineer to build and
optimize vision-based AI solutions including object detection, image segmentation,
and OCR systems. You will work closely with the product team to deploy vision models
in edge and cloud environments.""",
        """• 3-6 years of computer vision development experience.
• Expert knowledge of PyTorch or TensorFlow.
• Hands-on experience with YOLO, Detectron2, EfficientDet, or similar detectors.
• Proficiency in OpenCV for image processing.
• Experience with model optimization: TensorRT, ONNX, pruning, quantization.
• Familiarity with dataset management: COCO, LabelMe, Roboflow.
• Knowledge of deploying vision models on edge devices (Jetson, Raspberry Pi).
• Strong Python and C++ (for performance-critical modules) skills.""",
        "PyTorch, OpenCV, YOLO, TensorRT, ONNX, Python, Computer Vision, Deep Learning, CUDA",
        "full_time", "3-6", 100000, 190000, 2
    ),
    (
        "NLPCraft India", "Information Technology", "Delhi NCR",
        "NLP / LLM Engineer",
        """NLPCraft India is hiring an NLP / LLM Engineer to build natural language
understanding systems, integrate and fine-tune large language models (GPT-4, LLaMA,
Mistral), and develop GenAI-powered applications using LangChain and vector databases.
You will drive the NLP strategy and work with the research team.""",
        """• 3-6 years of NLP and/or LLM engineering experience.
• Expert Python skills with HuggingFace Transformers, LangChain, LlamaIndex.
• Experience fine-tuning LLMs (LoRA, QLoRA, PEFT).
• Knowledge of vector databases: Pinecone, Weaviate, Chroma, FAISS.
• Experience with RAG architectures and prompt engineering.
• Familiarity with embedding models (OpenAI, sentence-transformers).
• Strong mathematical background in NLP: attention, BERT, GPT architectures.
• Experience deploying models via REST APIs and managing GPU resources.""",
        "Python, LangChain, HuggingFace, LLM, RAG, Pinecone, FastAPI, NLP, PyTorch, LoRA",
        "full_time", "3-6", 100000, 200000, 2
    ),
    (
        "DataScience360", "Information Technology", "Bangalore, Karnataka",
        "Data Scientist",
        """DataScience360 is looking for a Data Scientist to extract actionable insights
from large datasets, build predictive models, and communicate findings to business
stakeholders. You will work on recommendation systems, customer segmentation, churn
prediction, and demand forecasting projects.""",
        """• 3-5 years of data science experience.
• Strong Python (Pandas, NumPy, scikit-learn, XGBoost, LightGBM) skills.
• Experience with statistical analysis, A/B testing, and hypothesis testing.
• Proficiency in data visualization: Matplotlib, Seaborn, Plotly, Power BI.
• Strong SQL skills and experience with cloud data warehouses (BigQuery, Redshift).
• Familiarity with deep learning frameworks (TensorFlow / PyTorch) is a plus.
• Experience with model deployment and MLOps practices.
• Excellent communication skills to present insights to non-technical stakeholders.""",
        "Python, scikit-learn, XGBoost, Pandas, SQL, Tableau, BigQuery, MLflow, Statistics",
        "full_time", "3-5", 80000, 150000, 2
    ),

    # -- Cybersecurity -------------------------------------------------------
    (
        "SecureGuard India", "Information Technology", "Hyderabad, Telangana",
        "Application Security (AppSec) Engineer",
        """SecureGuard India is seeking an Application Security Engineer to integrate
security practices into the software development lifecycle. You will conduct code reviews,
perform SAST/DAST scanning, run penetration tests, and work with development teams
to remediate vulnerabilities and build secure coding standards.""",
        """• 3-6 years of application security experience.
• Strong knowledge of OWASP Top 10, CWE, and secure coding practices.
• Experience with SAST tools: Checkmarx, SonarQube, Semgrep.
• Experience with DAST tools: OWASP ZAP, Burp Suite Pro.
• Proficiency in Python or Java for security automation.
• Experience with web application penetration testing.
• Familiarity with secrets management: HashiCorp Vault, AWS Secrets Manager.
• Security certifications (OSCP, CEH, GWEB) are a strong advantage.""",
        "OWASP, Burp Suite, SAST, DAST, Python, Penetration Testing, Checkmarx, AppSec",
        "full_time", "3-6", 90000, 170000, 2
    ),
    (
        "CyberShield Technologies", "Information Technology", "Bangalore, Karnataka",
        "SOC Analyst (Level 2)",
        """CyberShield Technologies is hiring a SOC Analyst (L2) to monitor, investigate,
and respond to security incidents. You will triage alerts from SIEM, perform threat
hunting, conduct in-depth investigation of security events, and escalate complex
incidents to the Tier 3 team.""",
        """• 2-4 years of SOC or incident response experience.
• Strong knowledge of SIEM platforms: Splunk, Microsoft Sentinel, or IBM QRadar.
• Experience with log analysis, threat hunting, and alert triage.
• Understanding of MITRE ATT&CK framework.
• Familiarity with EDR solutions (CrowdStrike Falcon, SentinelOne).
• Knowledge of network security: firewalls, IDS/IPS, DLP.
• CEH, CompTIA Security+, or Splunk Certified Power User certifications preferred.
• Strong analytical and report-writing skills.""",
        "SIEM, Splunk, Sentinel, MITRE ATT&CK, CrowdStrike, EDR, SOC, Threat Hunting, Python",
        "full_time", "2-4", 60000, 120000, 2
    ),
    (
        "NetDefend India", "Information Technology", "Pune, Maharashtra",
        "Cloud Security Engineer",
        """NetDefend India is looking for a Cloud Security Engineer to secure our AWS and
Azure environments. You will implement security controls, conduct cloud configuration
reviews, manage identity and access, perform security assessments, and ensure compliance
with CIS benchmarks and industry standards.""",
        """• 3-6 years of cloud security experience.
• Deep knowledge of AWS and/or Azure security services (GuardDuty, Security Hub, Defender).
• Experience with Cloud Security Posture Management (CSPM) tools: Prisma Cloud, Wiz.
• Strong understanding of IAM, VPC security, encryption, and secrets management.
• Experience with container security (Kubernetes RBAC, OPA/Gatekeeper, Falco).
• Knowledge of compliance frameworks: SOC 2, ISO 27001, PCI-DSS.
• AWS Security Specialty or Azure Security Engineer certifications preferred.
• Proficiency in Python or Terraform for security automation.""",
        "AWS Security, Azure Security, Prisma Cloud, IAM, Python, Terraform, CSPM, Kubernetes",
        "full_time", "3-6", 90000, 175000, 2
    ),

    # -- QA / Testing --------------------------------------------------------
    (
        "QualityFirst India", "Information Technology", "Bangalore, Karnataka",
        "Senior QA Engineer - API & Performance Testing",
        """QualityFirst India is hiring a Senior QA Engineer specializing in API and
performance testing. You will design comprehensive test strategies, build API automation
frameworks using RestAssured or Karate, conduct load and stress testing with JMeter or
k6, and report performance bottlenecks to the development team.""",
        """• 3-6 years of QA engineering experience with focus on API and performance testing.
• Expert knowledge of RestAssured, Karate DSL, or Postman/Newman for API testing.
• Strong experience with JMeter, k6, or Gatling for performance testing.
• Proficiency in Java or Python for test automation.
• Experience with CI/CD integration of test suites.
• Knowledge of test management tools: TestRail, Zephyr, or Xray.
• Understanding of microservices architecture and RESTful/GraphQL APIs.
• ISTQB Advanced Level (Test Manager or Technical Test Analyst) certification preferred.""",
        "RestAssured, JMeter, k6, Java, Python, API Testing, Performance Testing, CI/CD, Postman",
        "full_time", "3-6", 70000, 130000, 2
    ),
    (
        "AutoTest Labs", "Information Technology", "Chennai, Tamil Nadu",
        "Playwright / Cypress Test Automation Engineer",
        """AutoTest Labs is seeking a Test Automation Engineer proficient in Playwright or
Cypress to build end-to-end UI automation frameworks for our web applications. You will
collaborate with QA leads to design test architectures, maintain stable test suites,
and integrate tests into the CI/CD pipeline.""",
        """• 2-5 years of UI test automation experience.
• Strong proficiency in Playwright or Cypress.
• Knowledge of TypeScript/JavaScript for test scripting.
• Experience with Page Object Model (POM) and BDD frameworks (Cucumber, Gherkin).
• Familiarity with CI/CD integration: GitHub Actions, Jenkins.
• Experience with visual testing tools (Percy, Applitools) is a plus.
• Understanding of cross-browser and cross-device testing strategies.
• ISTQB Foundation or Agile Tester certification preferred.""",
        "Playwright, Cypress, TypeScript, JavaScript, BDD, Cucumber, GitHub Actions, POM",
        "full_time", "2-5", 60000, 120000, 2
    ),

    # -- Database / Backend Infrastructure ---------------------------------
    (
        "DBMasters India", "Information Technology", "Bangalore, Karnataka",
        "Database Administrator (DBA) - PostgreSQL / MySQL",
        """DBMasters India is hiring an experienced DBA to manage, optimize, and support our
critical PostgreSQL and MySQL database environments. You will handle database design,
performance tuning, high-availability configurations (replication, failover), backup
strategies, and security hardening.""",
        """• 3-6 years of DBA experience with PostgreSQL and/or MySQL.
• Deep expertise in query optimization, indexing, and execution plan analysis.
• Experience with replication (logical, streaming), HA setups (Patroni, Galera Cluster).
• Knowledge of backup strategies: pg_dump, Barman, Percona XtraBackup.
• Familiarity with monitoring tools: pg_stat_statements, Percona Monitoring.
• Experience with database migration and schema evolution tools (Flyway, Liquibase).
• Knowledge of database security: encryption, RBAC, auditing.
• Experience with cloud databases (AWS RDS/Aurora, GCP Cloud SQL) is a plus.""",
        "PostgreSQL, MySQL, Patroni, Replication, Query Optimization, Barman, Flyway, AWS RDS",
        "full_time", "3-6", 75000, 140000, 2
    ),
    (
        "GraphDB Solutions", "Information Technology", "Hyderabad, Telangana",
        "MongoDB / NoSQL Database Engineer",
        """GraphDB Solutions is looking for a NoSQL Database Engineer with deep MongoDB
expertise to design schemas, optimize queries, manage Atlas clusters, and build
efficient data access patterns for high-throughput applications. You will also work
with Redis for caching and Elasticsearch for search.""",
        """• 3-5 years of MongoDB and NoSQL engineering experience.
• Expert knowledge of MongoDB Atlas, aggregation pipelines, indexing strategies.
• Experience with MongoDB schema design patterns and performance tuning.
• Proficiency with Redis (caching, pub/sub, streams, Redis Cluster).
• Experience with Elasticsearch for full-text search and analytics.
• Knowledge of change streams and MongoDB replica set management.
• Familiarity with data modeling for document, key-value, and search use cases.
• Python or Java skills for database tooling and automation.""",
        "MongoDB, Atlas, Redis, Elasticsearch, Python, NoSQL, Aggregation Pipelines, Docker",
        "full_time", "3-5", 70000, 135000, 2
    ),

    # -- Networking / Systems -----------------------------------------------
    (
        "NetPro India", "Information Technology", "Mumbai, Maharashtra",
        "Network Engineer (CCNP Level)",
        """NetPro India is seeking a seasoned Network Engineer to design, implement, and
manage enterprise-grade network infrastructure including routing, switching, SD-WAN,
and network security. You will work on LAN/WAN optimization, troubleshoot complex
network issues, and support cloud connectivity.""",
        """• 4-7 years of enterprise network engineering experience.
• CCNP or equivalent certification (R&S, Enterprise, Security track).
• Expert knowledge of BGP, OSPF, EIGRP, MPLS, and VPN technologies.
• Experience with Cisco, Juniper, Fortinet, or Palo Alto network devices.
• Hands-on experience with SD-WAN (Cisco Viptela, VMware Velocloud).
• Knowledge of network security: firewall policies, IPS/IDS, NAC.
• Experience with network monitoring: SolarWinds, PRTG, Zabbix.
• Scripting for network automation: Python, Ansible, Netmiko.""",
        "CCNP, BGP, OSPF, SD-WAN, Cisco, Fortinet, Python, Ansible, Network Security, MPLS",
        "full_time", "4-7", 80000, 150000, 2
    ),
    (
        "CloudNet Solutions", "Information Technology", "Bangalore, Karnataka",
        "Linux System Administrator",
        """CloudNet Solutions requires an experienced Linux System Administrator to manage,
configure, and optimize our on-premises and cloud Linux server infrastructure. You will
handle user management, security hardening, performance tuning, automation with Ansible,
and ensure 99.9%+ uptime of critical services.""",
        """• 3-6 years of Linux system administration experience (RHEL/CentOS/Ubuntu).
• Strong knowledge of Linux internals, kernel tuning, and performance optimization.
• Experience with configuration management: Ansible, Puppet, or Chef.
• Familiarity with virtualization: KVM, VMware ESXi, or Proxmox.
• Knowledge of security hardening: CIS benchmarks, SELinux, auditd.
• Experience with high-availability clustering: Pacemaker, Corosync, HAProxy.
• Strong shell scripting (Bash) and Python automation skills.
• RHCE or LFCS certification preferred.""",
        "Linux, RHEL, Ansible, KVM, Bash, Python, HAProxy, SELinux, System Administration",
        "full_time", "3-6", 65000, 130000, 2
    ),

    # -- Java / Spring ------------------------------------------------------
    (
        "JavaCraft India", "Information Technology", "Bangalore, Karnataka",
        "Java Spring Boot Backend Developer",
        """JavaCraft India is hiring an experienced Java Spring Boot Developer to design and
implement microservices for our enterprise financial platform. You will develop RESTful
and GraphQL APIs, integrate with message queues, implement security with Spring Security
and OAuth2, and ensure high test coverage with JUnit and Mockito.""",
        """• 3-6 years of Java development with Spring Boot expertise.
• Strong understanding of Spring MVC, Spring Data JPA, Spring Security.
• Experience with microservices architecture and RESTful API design.
• Knowledge of message brokers: Kafka or RabbitMQ.
• Proficiency with PostgreSQL or MySQL and query optimization.
• Experience with Docker, Kubernetes, and CI/CD pipelines.
• Test-driven development with JUnit 5, Mockito, and Testcontainers.
• Knowledge of OAuth2/JWT authentication patterns.""",
        "Java, Spring Boot, Microservices, Kafka, PostgreSQL, Docker, JUnit, REST APIs, OAuth2",
        "full_time", "3-6", 75000, 145000, 3
    ),
    (
        "MicroServices Hub", "Information Technology", "Pune, Maharashtra",
        "Java Microservices Architect",
        """MicroServices Hub is looking for a Java Microservices Architect to lead the
design and implementation of distributed systems. You will make architectural decisions,
establish coding standards, define API contracts, design event-driven workflows with
Kafka, and mentor senior developers.""",
        """• 7+ years of Java development with 3+ years in an architect or tech lead role.
• Expert knowledge of Spring Boot, Spring Cloud, and microservices design patterns.
• Strong experience with Kubernetes, Docker, and service mesh (Istio).
• Expert knowledge of Apache Kafka for event-driven architecture.
• Experience with API gateways: Kong, AWS API Gateway, or Spring Cloud Gateway.
• Knowledge of distributed tracing: Jaeger, Zipkin, OpenTelemetry.
• Strong background in DDD, CQRS, Event Sourcing patterns.
• Excellent technical communication and stakeholder management skills.""",
        "Java, Spring Boot, Spring Cloud, Kafka, Kubernetes, Istio, DDD, CQRS, Microservices",
        "full_time", "7+", 150000, 250000, 1
    ),

    # -- .NET / Microsoft Stack --------------------------------------------
    (
        "DotNetPro India", "Information Technology", "Hyderabad, Telangana",
        "C# .NET Core API Developer",
        """DotNetPro India is hiring a .NET Core Developer to build high-performance REST
APIs and microservices for our logistics management platform. You will implement clean
architecture, Entity Framework Core for ORM, SignalR for real-time features, and deploy
to Azure using Azure DevOps pipelines.""",
        """• 3-6 years of .NET Core / C# development experience.
• Strong expertise in ASP.NET Core, Entity Framework Core, LINQ.
• Experience with clean architecture, CQRS, and MediatR.
• Familiarity with SignalR for real-time communication.
• Experience with Azure services: App Service, SQL Database, Service Bus.
• Knowledge of Docker and Kubernetes for containerized deployments.
• Test-driven development with xUnit and Moq.
• Experience with Azure DevOps for CI/CD pipelines.""",
        "C#, .NET Core, ASP.NET, EF Core, Azure, SignalR, CQRS, Docker, xUnit, REST APIs",
        "full_time", "3-6", 75000, 145000, 2
    ),
    (
        "AzureFirst Technologies", "Information Technology", "Bangalore, Karnataka",
        "Azure DevOps Engineer",
        """AzureFirst Technologies is seeking an Azure DevOps Engineer to manage and optimize
software delivery on the Microsoft Azure platform. You will build Azure Pipelines,
manage Azure infrastructure with Bicep/Terraform, implement monitoring with Azure Monitor
and Application Insights, and support containerized workloads on AKS.""",
        """• 3-6 years of Azure DevOps and cloud engineering experience.
• Expert knowledge of Azure Pipelines for CI/CD.
• Strong experience with AKS (Azure Kubernetes Service) and Helm.
• Proficiency in Bicep, ARM Templates, or Terraform for IaC on Azure.
• Experience with Azure Monitor, Application Insights, Log Analytics.
• Knowledge of Azure Repos, Azure Artifacts, and release management.
• Familiarity with Azure Active Directory and RBAC.
• AZ-400 (Azure DevOps Engineer Expert) certification preferred.""",
        "Azure DevOps, AKS, Kubernetes, Terraform, Bicep, Azure Monitor, Docker, CI/CD",
        "full_time", "3-6", 80000, 155000, 2
    ),

    # -- AI / Automation / GenAI -------------------------------------------
    (
        "GenAI Builders", "Information Technology", "Bangalore, Karnataka",
        "Generative AI / LLM Application Developer",
        """GenAI Builders is looking for a developer passionate about building production-grade
Generative AI applications. You will architect RAG systems, implement agentic workflows
using LangChain/LangGraph or AutoGen, fine-tune open-source LLMs, and deploy AI APIs
at scale. You will work with product managers to turn AI ideas into real features.""",
        """• 2-5 years of software development + 1+ years of LLM/GenAI application experience.
• Strong Python skills; FastAPI or Flask for API development.
• Hands-on experience with LangChain, LlamaIndex, or LangGraph.
• Experience with OpenAI API, Anthropic Claude, or open-source LLMs (LLaMA, Mistral).
• Knowledge of vector databases: Pinecone, Weaviate, Qdrant, or Chroma.
• Experience with prompt engineering, RAG architecture design, and evaluation metrics.
• Familiarity with fine-tuning (LoRA, QLoRA) using HuggingFace PEFT.
• Experience deploying AI services on AWS/GCP with Docker/Kubernetes.""",
        "Python, LangChain, LLM, RAG, OpenAI, FastAPI, Pinecone, Docker, HuggingFace, LoRA",
        "full_time", "2-5", 90000, 180000, 2
    ),
    (
        "RPA Innovate India", "Information Technology", "Pune, Maharashtra",
        "RPA Developer (UiPath / Automation Anywhere)",
        """RPA Innovate India is hiring an RPA Developer to automate repetitive business
processes using UiPath or Automation Anywhere. You will work with business analysts
to identify automation opportunities, develop and test bots, manage the Orchestrator,
and ensure bots are stable, monitored, and maintained in production.""",
        """• 2-5 years of RPA development experience.
• Strong proficiency in UiPath (Studio, Orchestrator, Action Center) or AA360.
• Experience with both attended and unattended automation development.
• Knowledge of VB.NET or C# for custom activities.
• Experience with API and database integration within RPA workflows.
• Understanding of process mining and process documentation (PDD, SDD).
• UiPath Advanced Developer or AA Master Certified Developer certification preferred.
• Good problem-solving skills and experience with production bot incident management.""",
        "UiPath, Automation Anywhere, RPA, Orchestrator, VB.NET, API Integration, Python",
        "full_time", "2-5", 55000, 110000, 3
    ),

    # -- Product / Project Management (IT) --------------------------------
    (
        "AgileEdge Technologies", "Information Technology", "Bangalore, Karnataka",
        "Technical Project Manager (IT)",
        """AgileEdge Technologies is looking for a Technical Project Manager with a strong
engineering background to drive delivery of complex software projects. You will manage
agile sprints, coordinate cross-functional teams, communicate with stakeholders, manage
risks, and ensure projects are delivered on time and within scope.""",
        """• 5-8 years of IT project management experience.
• PMP or Prince2 certification; CSM or SAFe Agilist is a strong plus.
• Technical background in software development (Java, Python, or .NET).
• Experience managing agile (Scrum/Kanban) delivery teams.
• Proficiency in Jira, Confluence, and MS Project.
• Strong stakeholder communication and executive reporting skills.
• Experience with risk management, dependency tracking, and escalation.
• Familiarity with cloud technologies (AWS, Azure, GCP) and DevOps practices.""",
        "Project Management, Agile, Scrum, Jira, PMP, Stakeholder Management, Risk Management",
        "full_time", "5-8", 100000, 180000, 1
    ),
    (
        "ProductMinds India", "Information Technology", "Bangalore, Karnataka",
        "Technical Product Manager",
        """ProductMinds India is seeking a Technical Product Manager to own the product
roadmap for our developer tooling platform. You will gather requirements, write detailed
product specifications, prioritize backlogs, work closely with engineering teams, and
define success metrics for each release.""",
        """• 4-7 years of product management experience with a technical background.
• Strong understanding of software development processes and APIs.
• Experience with agile methodologies, sprint planning, and backlog grooming.
• Ability to write detailed PRDs, user stories, and acceptance criteria.
• Experience with product analytics: Mixpanel, Amplitude, or Heap.
• Proficiency with Jira, Notion, and Figma for collaboration.
• Strong data-driven decision-making skills.
• Prior experience as a software developer is a significant advantage.""",
        "Product Management, Agile, Jira, PRD, API Knowledge, Analytics, Figma, User Stories",
        "full_time", "4-7", 110000, 200000, 1
    ),

    # -- UI/UX Design ------------------------------------------------------
    (
        "DesignSync India", "Information Technology", "Bangalore, Karnataka",
        "UI/UX Designer (SaaS Products)",
        """DesignSync India is hiring a UI/UX Designer to create beautiful, user-centered
designs for our B2B SaaS products. You will conduct user research, create wireframes and
prototypes in Figma, run usability tests, and collaborate with frontend engineers to
ensure pixel-perfect implementation.""",
        """• 2-5 years of UI/UX design experience, preferably for web and SaaS products.
• Expert proficiency in Figma (components, auto-layout, prototyping, design tokens).
• Strong understanding of UX principles, information architecture, and interaction design.
• Experience conducting user research, usability testing, and heuristic evaluation.
• Portfolio demonstrating end-to-end design case studies.
• Knowledge of accessibility standards (WCAG 2.1).
• Familiarity with design systems and component libraries.
• Basic HTML/CSS knowledge for effective collaboration with developers.""",
        "Figma, UI Design, UX Research, Prototyping, Design Systems, Accessibility, WCAG, Wireframing",
        "full_time", "2-5", 55000, 120000, 2
    ),

    # -- Embedded / IoT ----------------------------------------------------
    (
        "EmbedTech India", "Information Technology", "Pune, Maharashtra",
        "Embedded Software Engineer (C/C++)",
        """EmbedTech India is seeking an Embedded Software Engineer to develop firmware for
our IoT products built on ARM Cortex-M microcontrollers. You will write low-level C/C++
code for peripheral drivers, RTOS-based task scheduling, and wireless communication
stacks (BLE, Wi-Fi, LoRa).""",
        """• 3-6 years of embedded software development experience.
• Expert knowledge of C and C++ for microcontroller programming.
• Experience with ARM Cortex-M series MCUs (STM32, NRF52, ESP32).
• Strong understanding of FreeRTOS or Zephyr RTOS.
• Experience with communication protocols: SPI, I2C, UART, BLE, Wi-Fi, MQTT.
• Familiarity with bootloaders, OTA firmware updates, and power optimization.
• Experience with debugging tools: JTAG, SWD, logic analyzers.
• Knowledge of PCB bring-up and hardware/software co-design.""",
        "C, C++, FreeRTOS, ARM Cortex-M, BLE, IoT, MQTT, STM32, ESP32, Embedded Systems",
        "full_time", "3-6", 70000, 140000, 2
    ),
    (
        "IoTCloud India", "Information Technology", "Bangalore, Karnataka",
        "IoT Solutions Architect",
        """IoTCloud India is looking for an IoT Solutions Architect to design end-to-end IoT
solutions spanning edge devices, connectivity, cloud ingestion, and data visualization.
You will work with enterprise clients to architect scalable IoT platforms on AWS IoT
Core or Azure IoT Hub and drive technical pre-sales.""",
        """• 5-8 years of IoT or embedded systems experience.
• Strong knowledge of IoT protocols: MQTT, CoAP, AMQP, OPC-UA.
• Experience with AWS IoT Core, Azure IoT Hub, or Google Cloud IoT.
• Familiarity with edge computing platforms: AWS Greengrass, Azure IoT Edge.
• Knowledge of device provisioning, certificate management, and secure boot.
• Experience with time-series databases: InfluxDB, TimescaleDB, or AWS Timestream.
• Strong Python and/or Node.js skills.
• AWS IoT Specialty or Azure IoT Developer certifications preferred.""",
        "IoT, MQTT, AWS IoT Core, Azure IoT Hub, Python, Edge Computing, InfluxDB, Node.js",
        "full_time", "5-8", 110000, 200000, 1
    ),

    # -- Blockchain / Web3 -------------------------------------------------
    (
        "BlockChain Labs India", "Information Technology", "Bangalore, Karnataka",
        "Solidity / Smart Contract Developer",
        """BlockChain Labs India is seeking a Solidity Developer to build, test, and deploy
smart contracts for our DeFi and NFT platform. You will work on ERC-20/ERC-721/ERC-1155
contracts, implement complex DeFi mechanics, write comprehensive Hardhat tests, and
conduct gas optimization.""",
        """• 2-4 years of Solidity and smart contract development experience.
• Expert knowledge of ERC-20, ERC-721, ERC-1155, and EIP standards.
• Strong experience with Hardhat, Foundry, or Truffle development frameworks.
• Understanding of DeFi protocols: AMMs, lending, yield farming.
• Knowledge of smart contract security and common vulnerabilities (reentrancy, overflow).
• Experience with OpenZeppelin contracts library.
• Familiarity with Layer 2 solutions: Polygon, Arbitrum, Optimism.
• JavaScript/TypeScript skills for frontend Web3 integration (ethers.js, wagmi).""",
        "Solidity, Hardhat, Foundry, ERC-20, DeFi, Smart Contracts, Web3.js, Ethereum, OpenZeppelin",
        "full_time", "2-4", 100000, 200000, 2
    ),

    # -- IT Support / Helpdesk ---------------------------------------------
    (
        "TechSupport Pro India", "Information Technology", "Bangalore, Karnataka",
        "IT Support Engineer (L2)",
        """TechSupport Pro India is hiring an L2 IT Support Engineer to provide second-level
technical support for hardware, software, networking, and cloud services. You will handle
escalated tickets from the L1 team, manage Active Directory, configure Microsoft 365,
and maintain our corporate IT infrastructure.""",
        """• 2-4 years of IT support or systems administration experience.
• Strong knowledge of Windows Server (AD, DNS, DHCP, GPO) and Microsoft 365.
• Experience with ITSM tools: ServiceNow, Freshservice, or Jira Service Management.
• Familiarity with Azure AD (Entra ID), Intune, and Microsoft Endpoint Manager.
• Networking knowledge: TCP/IP, VPN, Wi-Fi troubleshooting.
• Basic knowledge of PowerShell scripting for automation.
• Experience with endpoint security and antivirus management.
• CompTIA A+, Network+, or Microsoft MCP certifications preferred.""",
        "Windows Server, Active Directory, Microsoft 365, Azure AD, PowerShell, ITSM, Networking",
        "full_time", "2-4", 35000, 70000, 3
    ),
    (
        "CloudDesk India", "Information Technology", "Remote",
        "Cloud Support Specialist (AWS)",
        """CloudDesk India is looking for a Cloud Support Specialist to assist customers in
troubleshooting and optimizing their AWS environments. You will work on billing, IAM,
EC2, RDS, S3, Lambda, and networking issues-providing expert guidance via tickets,
chat, and calls to help clients maximize their AWS investment.""",
        """• 2-4 years of AWS cloud support or administration experience.
• AWS Solutions Architect Associate or SysOps Administrator certification.
• Strong knowledge of EC2, S3, RDS, IAM, VPC, CloudFront, Lambda.
• Experience with AWS CloudWatch for monitoring and alerting.
• Familiarity with Infrastructure as Code: Terraform or CloudFormation.
• Strong analytical and troubleshooting skills.
• Excellent written and verbal communication skills for customer interaction.
• Knowledge of Linux and basic scripting (Bash, Python) for diagnostics.""",
        "AWS, EC2, S3, RDS, IAM, VPC, Lambda, Python, Terraform, CloudWatch, Linux",
        "full_time", "2-4", 45000, 90000, 3
    ),

    # -- Internships --------------------------------------------------------
    (
        "StartupNest India", "Information Technology", "Bangalore, Karnataka",
        "Software Development Intern (Python / Django)",
        """StartupNest India is offering a 6-month paid internship for passionate
Computer Science students or fresh graduates to work on real-world projects. You will
build REST APIs, work with databases, write tests, and contribute to product features
under the guidance of senior engineers.""",
        """• Pursuing or recently completed B.Tech / B.E. / M.Tech in CS or IT.
• Basic knowledge of Python and understanding of web concepts.
• Familiarity with Django or Flask is a plus.
• Knowledge of SQL and basic database operations.
• Understanding of version control (Git) and collaborative coding.
• Strong problem-solving skills and eagerness to learn.
• Good communication skills for team collaboration.
• Availability for a 6-month full-time internship (remote/hybrid).""",
        "Python, Django, SQL, Git, REST APIs, HTML, CSS, JavaScript",
        "internship", "fresher", 15000, 25000, 5
    ),
    (
        "TechBloom India", "Information Technology", "Pune, Maharashtra",
        "Data Science Intern",
        """TechBloom India is offering a Data Science internship for students and freshers
eager to kickstart their careers in AI/ML. You will assist the data team with EDA,
feature engineering, model training, and visualization tasks on real company datasets.""",
        """• Pursuing or recently completed B.Tech / MCA / M.Sc in CS, IT, Statistics, or Mathematics.
• Proficiency in Python (Pandas, NumPy, Matplotlib, Seaborn, scikit-learn).
• Knowledge of machine learning concepts: regression, classification, clustering.
• Familiarity with Jupyter Notebooks and Google Colab.
• Basic SQL knowledge.
• Strong analytical and mathematical aptitude.
• Good communication skills for presenting findings.
• Participation in Kaggle competitions is a plus.""",
        "Python, Pandas, NumPy, scikit-learn, Matplotlib, SQL, Jupyter, Machine Learning",
        "internship", "fresher", 10000, 20000, 5
    ),
    (
        "ReactForward India", "Information Technology", "Remote",
        "Frontend Development Intern (React.js)",
        """ReactForward India is hiring Frontend Interns with a passion for building beautiful
UIs. You will work on live product features using React.js, contribute to the component
library, fix bugs, and integrate APIs-learning modern frontend development in a
fast-paced startup environment.""",
        """• Pursuing or recently completed B.Tech / BCA / B.Sc in CS or IT.
• Basic to intermediate knowledge of HTML5, CSS3, and JavaScript (ES6+).
• Familiarity with React.js fundamentals (components, hooks, props, state).
• Understanding of REST API consumption with Axios or Fetch.
• Knowledge of Git version control.
• Basic understanding of responsive design (Flexbox, CSS Grid).
• Portfolio or GitHub projects demonstrating frontend work preferred.
• Good communication skills and willingness to receive feedback.""",
        "React.js, JavaScript, HTML5, CSS3, Git, REST APIs, Responsive Design",
        "internship", "fresher", 10000, 20000, 5
    ),
]


class Command(BaseCommand):
    help = "Seed 50+ IT-domain jobs (idempotent - skips existing titles)."

    # Map human-readable experience strings to model EXPERIENCE_CHOICES values
    EXPERIENCE_MAP = {
        "fresher": "fresher",
        "1-2": "1-2",
        "2-4": "3-5",  # closest choice
        "2-5": "3-5",
        "3-5": "3-5",
        "3-6": "5-8",
        "4-7": "5-8",
        "5-8": "5-8",
        "7+":  "8+",
        "7-10": "8+",
        "8+": "8+",
    }

    def _get_or_create_employer(self, company, industry, location):
        slug = company.lower().replace(" ", "_").replace("&", "and")[:30]
        username = f"sys_it_{slug}"
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"first_name": company, "is_active": True},
        )
        if not user.has_usable_password():
            user.set_unusable_password()
            user.save()
        emp, _ = EmployerProfile.objects.get_or_create(
            user=user,
            defaults={
                "company_name": company,
                "industry": industry,
                "location": location,
                "description": f"System-seeded employer for {company}.",
                "company_website": "",
                "company_size": "51-200",
            },
        )
        return emp

    def handle(self, *args, **options):
        created = skipped = 0
        for (
            company, industry, location, title,
            description, requirements, skills,
            job_type, experience, salary_min, salary_max, openings
        ) in IT_JOBS:
            if JobPosting.objects.filter(title=title, is_seeded=True).exists():
                skipped += 1
                self.stdout.write(self.style.WARNING(f"  SKIP (exists): {title}"))
                continue

            emp = self._get_or_create_employer(company, industry, location)
            exp_choice = self.EXPERIENCE_MAP.get(experience, "fresher")
            JobPosting.objects.create(
                employer=emp,
                title=title,
                description=description,
                requirements=requirements,
                skills_required=skills,
                job_type=job_type,
                experience=exp_choice,
                location=location,
                salary_min=salary_min,
                salary_max=salary_max,
                openings=openings,
                status="active",
                is_seeded=True,
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(f"  CREATED: {title}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! Created {created} IT jobs, skipped {skipped} existing."
            )
        )
