import sys
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("cert-quiz-topics")

# Edit this per certification. domain should match the exam guide's domain names
# so the Bedrock prompt can reference them accurately.
TOPIC_SEED = {
    # Foundational
    "CLF-C02": [
        ("AWS Cloud concepts and shared responsibility model", "Cloud Concepts"),
        ("AWS pricing, billing, and support plans", "Billing and Pricing"),
        ("AWS global infrastructure and regions", "Technology"),
        ("AWS security and compliance basics", "Security and Compliance"),
    ],
    "AIF-C01": [
        ("Fundamentals of AI and ML on AWS", "Fundamentals of AI and ML"),
        ("Generative AI concepts and foundation models", "Fundamentals of Generative AI"),
        ("Applications of foundation models", "Applications of Foundation Models"),
        ("Responsible AI guidelines", "Guidelines for Responsible AI"),
    ],
    # Associate
    "SAA-C03": [
        # Domain 1: Design Secure Architectures (30%)
        ("IAM roles vs IAM policies vs resource policies", "Design Secure Architectures"),
        ("VPC subnets, route tables and NACLs", "Design Secure Architectures"),
        ("CloudFront origin access control", "Design Secure Architectures"),
        ("AWS KMS key management and envelope encryption", "Design Secure Architectures"),
        ("Secrets Manager vs Parameter Store for secrets management", "Design Secure Architectures"),
        ("AWS Organizations and service control policies (SCPs)", "Design Secure Architectures"),
        ("VPC endpoints (Gateway vs Interface) for private access", "Design Secure Architectures"),
        ("AWS WAF and Shield for DDoS and web protection", "Design Secure Architectures"),
        ("Security groups vs NACLs for traffic filtering", "Design Secure Architectures"),
        # Domain 2: Design Resilient Architectures (26%)
        ("S3 storage classes and lifecycle policies", "Design Resilient Architectures"),
        ("RDS Multi-AZ vs read replicas", "Design Resilient Architectures"),
        ("Multi-region disaster recovery strategies (RTO and RPO)", "Design Resilient Architectures"),
        ("Elastic Load Balancing (ALB vs NLB vs GWLB)", "Design Resilient Architectures"),
        ("Route 53 routing policies (failover, geolocation, latency)", "Design Resilient Architectures"),
        ("EBS vs EFS vs FSx for resilient storage", "Design Resilient Architectures"),
        ("DynamoDB global tables for multi-region resilience", "Design Resilient Architectures"),
        ("AWS Backup for cross-region backup strategies", "Design Resilient Architectures"),
        # Domain 3: Design High-Performing Architectures (24%)
        ("Auto Scaling groups and launch templates", "Design High-Performing Architectures"),
        ("SQS standard vs FIFO queues", "Design High-Performing Architectures"),
        ("ElastiCache (Redis vs Memcached) for caching", "Design High-Performing Architectures"),
        ("Kinesis Data Streams for high-throughput ingestion", "Design High-Performing Architectures"),
        ("Lambda performance and provisioned concurrency", "Design High-Performing Architectures"),
        ("DynamoDB partition keys and GSI design for performance", "Design High-Performing Architectures"),
        ("EC2 placement groups (cluster vs spread vs partition)", "Design High-Performing Architectures"),
        # Domain 4: Design Cost-Optimized Architectures (20%)
        ("Cost optimization with Savings Plans vs Reserved Instances", "Design Cost-Optimized Architectures"),
        ("Spot Instances and Spot Fleet strategies", "Design Cost-Optimized Architectures"),
        ("S3 lifecycle policies for cost optimization", "Design Cost-Optimized Architectures"),
        ("AWS Compute Optimizer for right-sizing", "Design Cost-Optimized Architectures"),
        ("NAT Gateway vs NAT Instance cost tradeoffs", "Design Cost-Optimized Architectures"),
        ("AWS Budgets and Cost Explorer for cost monitoring", "Design Cost-Optimized Architectures"),
    ],
    "DVA-C02": [
        ("Lambda cold starts and provisioned concurrency", "Development with AWS Services"),
        ("DynamoDB partition keys and hot partitions", "Development with AWS Services"),
        ("API Gateway throttling and usage plans", "Security"),
        ("CodeDeploy deployment strategies", "Deployment"),
        ("X-Ray tracing and distributed debugging", "Troubleshooting and Optimization"),
    ],
    "SOA-C02": [
        ("CloudWatch monitoring and alarms", "Monitoring and Reporting"),
        ("Auto Scaling and Elastic Load Balancing", "High Availability and Fault Tolerance"),
        ("AWS Systems Manager automation", "Deployment and Provisioning"),
        ("AWS Config and compliance checks", "Security and Compliance"),
    ],
    "SOA-C03": [
        ("Cloud operations and automation", "Cloud Operations"),
        ("Observability and monitoring strategies", "Observability"),
        ("Infrastructure as Code with CloudFormation", "Deployment"),
        ("Operational excellence practices", "Operational Excellence"),
    ],
    "DEA-C01": [
        ("Data ingestion with Kinesis and Glue", "Data Ingestion"),
        ("Data transformation and ETL", "Data Transformation"),
        ("Data storage with S3 and Redshift", "Data Storage"),
        ("Data security and governance", "Data Security"),
    ],
    "MLA-C01": [
        ("Data preparation for ML", "Data Preparation"),
        ("Model training and tuning", "Model Training"),
        ("Model deployment and inference", "Model Deployment"),
        ("ML operations and monitoring", "ML Operations"),
    ],
    # Professional
    "SAP-C02": [
        ("Multi-account AWS architectures", "Design Solutions for Organizational Complexity"),
        ("Hybrid cloud and migration strategies", "Design for Migration"),
        ("Cost optimization at scale", "Design for Cost Optimization"),
        ("Disaster recovery and business continuity", "Design for Resilience"),
    ],
    "DOP-C02": [
        ("CI/CD pipelines with CodePipeline", "CI/CD"),
        ("Infrastructure automation and configuration management", "Automation"),
        ("Monitoring, logging, and observability", "Observability"),
        ("Security automation and compliance", "Security"),
    ],
    "AIP-C01": [
        ("Generative AI architecture patterns", "Generative AI Architecture"),
        ("Foundation model customization and fine-tuning", "Foundation Models"),
        ("AI application security and governance", "Security and Governance"),
        ("Production deployment of AI workloads", "Deployment"),
    ],
    # Specialty
    "ANS-C01": [
        ("VPC design and hybrid networking", "Networking Design"),
        ("Direct Connect and VPN configurations", "Hybrid Connectivity"),
        ("Network security with NACLs and security groups", "Network Security"),
        ("Routing protocols and BGP", "Routing"),
    ],
    "SCS-C03": [
        ("Identity and access management at scale", "Identity and Access Management"),
        ("Data protection and encryption strategies", "Data Protection"),
        ("Incident response and forensics", "Incident Response"),
        ("Security automation and compliance", "Security Automation"),
    ],
    "MLS-C01": [
        ("Data engineering for ML", "Data Engineering"),
        ("Feature engineering and selection", "Feature Engineering"),
        ("Model evaluation and optimization", "Model Evaluation"),
        ("ML deployment patterns", "ML Deployment"),
    ],
    "DBS-C01": [
        ("Database design and migration", "Database Design"),
        ("Performance tuning and optimization", "Performance"),
        ("Backup, recovery, and high availability", "High Availability"),
        ("Security and compliance for databases", "Security"),
    ],
    "DAS-C01": [
        ("Data ingestion and collection", "Data Ingestion"),
        ("Data storage and cataloging", "Data Storage"),
        ("Data processing and transformation", "Data Processing"),
        ("Data analysis and visualization", "Data Analysis"),
    ],
}


def seed(cert_code):
    topics = TOPIC_SEED.get(cert_code)
    if not topics:
        print(f"No seed topics defined for {cert_code}, add them to TOPIC_SEED first.")
        return

    for topic, domain in topics:
        table.put_item(Item={
            "cert_code": cert_code,
            "topic": topic,
            "domain": domain,
            "box": 1,
            "next_due": "2026-01-01",  # forces it due on the very first run
            "last_reviewed": None,
        })
    print(f"Seeded {len(topics)} topics for {cert_code}")


if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else "SAA-C03")
