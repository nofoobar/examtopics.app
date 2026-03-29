"""
Seed script — run once to populate sample data.
Usage: pipenv run python seed.py
"""
from sqlmodel import Session, select
from db.database import engine
from db.models.exam import Vendor, Exam, Test, Question, QuestionType


# ── helpers ──────────────────────────────────────────────────────────────────

def already_seeded(session: Session) -> bool:
    return session.exec(select(Vendor)).first() is not None


# ── data ─────────────────────────────────────────────────────────────────────

VENDORS = [
    {"name": "Amazon Web Services", "slug": "aws",      "description": "Cloud computing services by Amazon."},
    {"name": "Microsoft",           "slug": "microsoft","description": "Cloud and software certifications by Microsoft."},
    {"name": "CompTIA",             "slug": "comptia",  "description": "Vendor-neutral IT certifications."},
    {"name": "Google",              "slug": "google",   "description": "Cloud certifications by Google."},
]

# Each exam: (vendor_slug, name, exam_code, slug, short_description)
EXAMS = [
    ("aws",       "AWS Certified Solutions Architect – Associate", "SAA-C03", "aws-saa-c03",
     "Design resilient, cost-optimised AWS architectures."),
    ("aws",       "AWS Certified Cloud Practitioner",              "CLF-C02", "aws-clf-c02",
     "Foundational overview of AWS Cloud concepts."),
    ("microsoft", "Microsoft Azure Fundamentals",                  "AZ-900",  "az-900",
     "Core Azure concepts and services."),
    ("microsoft", "Microsoft Azure Administrator",                 "AZ-104",  "az-104",
     "Implement, manage and monitor Azure environments."),
    ("comptia",   "CompTIA Security+",                             "SY0-701", "comptia-security-plus",
     "Entry-level cybersecurity certification."),
    ("comptia",   "CompTIA Network+",                              "N10-009", "comptia-network-plus",
     "Networking concepts, infrastructure and troubleshooting."),
    ("google",    "Google Cloud Associate Cloud Engineer",         "ACE",     "gcp-ace",
     "Deploy and manage applications on Google Cloud."),
]

# Each test: (exam_slug, name, slug, instructions)
TESTS = [
    ("aws-saa-c03", "Practice Test 1", "aws-saa-c03-pt1", "65 questions · 130 minutes · passing score 72%"),
    ("aws-saa-c03", "Practice Test 2", "aws-saa-c03-pt2", "65 questions · 130 minutes · passing score 72%"),
    ("aws-clf-c02", "Practice Test 1", "aws-clf-c02-pt1", "65 questions · 90 minutes · passing score 70%"),
    ("az-900",      "Practice Test 1", "az-900-pt1",      "60 questions · 60 minutes · passing score 70%"),
    ("az-104",      "Practice Test 1", "az-104-pt1",      "60 questions · 120 minutes · passing score 70%"),
    ("comptia-security-plus", "Practice Test 1", "security-plus-pt1", "90 questions · 90 minutes · passing score 75%"),
    ("comptia-network-plus",  "Practice Test 1", "network-plus-pt1",  "90 questions · 90 minutes · passing score 72%"),
    ("gcp-ace",     "Practice Test 1", "gcp-ace-pt1",     "50 questions · 120 minutes · passing score 70%"),
]

# Each question: (test_slug, question_text, q_type, options, correct_options, explanations, overall_explanation, domain)
QUESTIONS = [
    # ── AWS SAA-C03 PT1 ────────────────────────────────────────────────────
    (
        "aws-saa-c03-pt1",
        "A company needs to store frequently accessed data with millisecond latency and automatic scaling. "
        "Which AWS service is the BEST fit?",
        QuestionType.multiple_choice,
        {"1": "Amazon S3", "2": "Amazon DynamoDB", "3": "Amazon Glacier", "4": "AWS Snowball"},
        [2],
        {"1": "S3 is object storage and does not provide millisecond in-memory latency.",
         "2": "DynamoDB is a fully managed NoSQL database with single-digit millisecond performance and auto-scaling.",
         "3": "Glacier is archival storage — retrieval can take minutes to hours.",
         "4": "Snowball is a physical data transfer device, not a database."},
        "Amazon DynamoDB is purpose-built for high-throughput, low-latency workloads with seamless auto-scaling.",
        "Databases",
    ),
    (
        "aws-saa-c03-pt1",
        "Which AWS service allows you to run code without provisioning or managing servers?",
        QuestionType.multiple_choice,
        {"1": "Amazon EC2", "2": "Amazon ECS", "3": "AWS Lambda", "4": "Amazon Lightsail"},
        [3],
        {"1": "EC2 requires you to provision and manage virtual machine instances.",
         "2": "ECS runs containers but still requires cluster management.",
         "3": "Lambda is serverless — you upload code and AWS handles all infrastructure.",
         "4": "Lightsail is a simplified VPS service, not serverless."},
        "AWS Lambda is the core serverless compute service on AWS — no server management required.",
        "Compute",
    ),
    (
        "aws-saa-c03-pt1",
        "A solutions architect needs to ensure an application remains available during an Availability Zone failure. "
        "Which TWO actions should be taken?",
        QuestionType.multi_select,
        {"1": "Deploy EC2 instances in a single AZ",
         "2": "Use an Auto Scaling group spanning multiple AZs",
         "3": "Place an Application Load Balancer in front of the instances",
         "4": "Store all state in instance local storage"},
        [2, 3],
        {"1": "Single AZ deployment has no redundancy — an AZ failure takes down the whole application.",
         "2": "An ASG across multiple AZs automatically replaces failed instances in healthy AZs.",
         "3": "An ALB distributes traffic to healthy instances and routes around failed AZs.",
         "4": "Local instance storage is ephemeral and lost when an instance terminates."},
        "Multi-AZ Auto Scaling combined with a load balancer is the standard high-availability pattern on AWS.",
        "High Availability",
    ),
    # ── AWS SAA-C03 PT2 ────────────────────────────────────────────────────
    (
        "aws-saa-c03-pt2",
        "Which S3 storage class is most cost-effective for data that is accessed less than once a month "
        "but requires rapid retrieval when needed?",
        QuestionType.multiple_choice,
        {"1": "S3 Standard", "2": "S3 Standard-IA", "3": "S3 Glacier Instant Retrieval", "4": "S3 Glacier Deep Archive"},
        [3],
        {"1": "S3 Standard is optimised for frequent access — higher cost for infrequent workloads.",
         "2": "Standard-IA charges a retrieval fee and suits monthly-or-less access but retrieval is not instant.",
         "3": "Glacier Instant Retrieval offers archive pricing with millisecond retrieval — perfect here.",
         "4": "Deep Archive has the lowest cost but retrieval takes 12–48 hours."},
        "S3 Glacier Instant Retrieval is designed exactly for rarely accessed data that still needs fast retrieval.",
        "Storage",
    ),
    # ── AWS CLF-C02 PT1 ────────────────────────────────────────────────────
    (
        "aws-clf-c02-pt1",
        "Under the AWS Shared Responsibility Model, which of the following is the customer's responsibility?",
        QuestionType.multiple_choice,
        {"1": "Physical security of data centres",
         "2": "Patching the hypervisor",
         "3": "Configuring security groups",
         "4": "Maintaining network hardware"},
        [3],
        {"1": "AWS is fully responsible for physical data centre security.",
         "2": "The hypervisor is part of AWS infrastructure — AWS patches it.",
         "3": "Security groups are a customer-managed control — the customer configures them.",
         "4": "Network hardware is owned and maintained by AWS."},
        "Customers own configuration of the services they use; AWS owns the underlying infrastructure.",
        "Cloud Concepts",
    ),
    (
        "aws-clf-c02-pt1",
        "What is the AWS service that provides a virtual network dedicated to your AWS account?",
        QuestionType.multiple_choice,
        {"1": "AWS Direct Connect", "2": "Amazon VPC", "3": "AWS Transit Gateway", "4": "Amazon Route 53"},
        [2],
        {"1": "Direct Connect is a dedicated physical network link from on-premises to AWS.",
         "2": "Amazon VPC (Virtual Private Cloud) is a logically isolated virtual network within AWS.",
         "3": "Transit Gateway connects multiple VPCs and on-premises networks.",
         "4": "Route 53 is a DNS and traffic routing service."},
        "Amazon VPC lets you define your own IP ranges, subnets, route tables and gateways.",
        "Networking",
    ),
    # ── AZ-900 PT1 ────────────────────────────────────────────────────────
    (
        "az-900-pt1",
        "Which Azure service provides scalable cloud storage for unstructured data such as images and videos?",
        QuestionType.multiple_choice,
        {"1": "Azure SQL Database", "2": "Azure Blob Storage", "3": "Azure Table Storage", "4": "Azure Queue Storage"},
        [2],
        {"1": "Azure SQL Database is a relational database service, not for unstructured files.",
         "2": "Blob Storage is object storage designed for large volumes of unstructured data.",
         "3": "Table Storage is a NoSQL key-value store, not optimised for binary files.",
         "4": "Queue Storage is a messaging service for decoupling application components."},
        "Azure Blob Storage is the go-to service for storing images, videos, logs and other unstructured data at scale.",
        "Storage",
    ),
    (
        "az-900-pt1",
        "What does high availability mean in the context of Azure?",
        QuestionType.multiple_choice,
        {"1": "The ability to recover from a complete region failure within one hour",
         "2": "Ensuring resources are accessible with minimal downtime",
         "3": "Scaling resources up automatically when demand increases",
         "4": "Replicating data to at least three storage accounts"},
        [2],
        {"1": "That describes disaster recovery, not high availability.",
         "2": "High availability means services remain accessible and operational with minimal planned or unplanned downtime.",
         "3": "That describes auto-scaling / elasticity.",
         "4": "That is a specific storage redundancy feature, not the general definition of HA."},
        "High availability focuses on maximising uptime through redundancy, failover and health monitoring.",
        "Cloud Concepts",
    ),
    # ── Security+ PT1 ─────────────────────────────────────────────────────
    (
        "security-plus-pt1",
        "A user receives an email that appears to be from their bank, asking them to verify their credentials "
        "by clicking a link. What type of attack is this?",
        QuestionType.multiple_choice,
        {"1": "Vishing", "2": "Smishing", "3": "Phishing", "4": "Whaling"},
        [3],
        {"1": "Vishing is voice phishing — carried out over a phone call.",
         "2": "Smishing is phishing via SMS text message.",
         "3": "Phishing is a fraudulent email impersonating a trusted entity to steal credentials.",
         "4": "Whaling is phishing specifically targeting high-profile executives."},
        "Email-based credential theft via impersonation is the classic definition of phishing.",
        "Threats & Attacks",
    ),
    (
        "security-plus-pt1",
        "Which cryptographic concept ensures that a sender cannot deny having sent a message?",
        QuestionType.multiple_choice,
        {"1": "Confidentiality", "2": "Integrity", "3": "Non-repudiation", "4": "Availability"},
        [3],
        {"1": "Confidentiality ensures only authorised parties can read the data.",
         "2": "Integrity ensures the data has not been altered.",
         "3": "Non-repudiation prevents the sender from denying their action — achieved via digital signatures.",
         "4": "Availability ensures systems and data are accessible when needed."},
        "Non-repudiation is commonly implemented with digital signatures tied to a private key the sender alone holds.",
        "Cryptography",
    ),
    # ── Network+ PT1 ──────────────────────────────────────────────────────
    (
        "network-plus-pt1",
        "Which protocol operates at Layer 3 of the OSI model and is responsible for logical addressing and routing?",
        QuestionType.multiple_choice,
        {"1": "Ethernet", "2": "TCP", "3": "IP", "4": "HTTP"},
        [3],
        {"1": "Ethernet operates at Layer 2 (Data Link) and handles MAC addressing.",
         "2": "TCP operates at Layer 4 (Transport) and provides reliable delivery.",
         "3": "IP (Internet Protocol) operates at Layer 3 and handles logical (IP) addressing and routing.",
         "4": "HTTP operates at Layer 7 (Application)."},
        "IP is the fundamental Layer 3 protocol — every routed packet carries a source and destination IP address.",
        "OSI Model",
    ),
    # ── GCP ACE PT1 ───────────────────────────────────────────────────────
    (
        "gcp-ace-pt1",
        "Which GCP service should you use to run a containerised application without managing the underlying nodes?",
        QuestionType.multiple_choice,
        {"1": "Compute Engine", "2": "Google Kubernetes Engine (Autopilot)", "3": "Cloud Functions", "4": "App Engine Standard"},
        [2],
        {"1": "Compute Engine provides VMs — you manage the OS and infrastructure yourself.",
         "2": "GKE Autopilot manages nodes automatically; you only define workloads.",
         "3": "Cloud Functions is event-driven serverless — not designed for long-running containerised apps.",
         "4": "App Engine Standard runs web apps but abstracts away containers entirely."},
        "GKE Autopilot is Google's fully managed Kubernetes offering — no node provisioning or patching required.",
        "Compute",
    ),
]


# ── seed ─────────────────────────────────────────────────────────────────────

def seed():
    with Session(engine) as session:
        if already_seeded(session):
            print("Database already seeded — skipping.")
            return

        # 1. Vendors
        vendor_map: dict[str, Vendor] = {}
        for v in VENDORS:
            vendor = Vendor(**v)
            session.add(vendor)
            session.flush()
            vendor_map[v["slug"]] = vendor
        print(f"  ✓ {len(VENDORS)} vendors")

        # 2. Exams
        exam_map: dict[str, Exam] = {}
        for vendor_slug, name, code, slug, short_desc in EXAMS:
            exam = Exam(
                vendor_id=vendor_map[vendor_slug].id,
                name=name,
                exam_code=code,
                slug=slug,
                short_description=short_desc,
            )
            session.add(exam)
            session.flush()
            exam_map[slug] = exam
        print(f"  ✓ {len(EXAMS)} exams")

        # 3. Tests
        test_map: dict[str, Test] = {}
        for exam_slug, name, slug, instructions in TESTS:
            test = Test(
                exam_id=exam_map[exam_slug].id,
                name=name,
                slug=slug,
                instructions=instructions,
            )
            session.add(test)
            session.flush()
            test_map[slug] = test
        print(f"  ✓ {len(TESTS)} tests")

        # 4. Questions
        for test_slug, question_text, q_type, options, correct_options, explanations, overall, domain in QUESTIONS:
            question = Question(
                test_id=test_map[test_slug].id,
                question=question_text,
                question_type=q_type,
                options=options,
                correct_options=correct_options,
                explanations=explanations,
                overall_explanation=overall,
                domain=domain,
            )
            session.add(question)
        print(f"  ✓ {len(QUESTIONS)} questions")

        session.commit()
        print("\nSeed complete ✅")


if __name__ == "__main__":
    seed()
