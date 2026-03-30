"""Vendor (issuer) seed script for testmaker.

Usage:
    pipenv run python seed_vendors.py              # insert only missing vendors
    pipenv run python seed_vendors.py --reset      # drop ALL vendors then re-insert
    pipenv run python seed_vendors.py --dry-run    # print what would happen, touch nothing

Design notes:
  - Idempotent by default: existing slugs are skipped, not duplicated.
  - --reset deletes all vendors (and cascades to exams if your DB has ON DELETE
    CASCADE; otherwise raises an FK error - remove exams first).
  - is_popular=True vendors are highlighted on the homepage hero.
"""
import argparse
import sys
from sqlmodel import Session, select
from db.database import engine
from db.models.exam import Vendor


# ---------------------------------------------------------------------------
# Master vendor list
# ---------------------------------------------------------------------------

VENDORS: list[dict] = [
    # -- Cloud ---------------------------------------------------------------
    {
        "name":        "Amazon Web Services",
        "slug":        "aws",
        "description": "Industry-leading cloud platform with 200+ services covering compute, storage, databases, ML and more.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "Microsoft",
        "slug":        "microsoft",
        "description": "Cloud and enterprise software certifications spanning Azure, Microsoft 365, Dynamics and security.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "Google",
        "slug":        "google",
        "description": "Google Cloud certifications covering data engineering, infrastructure, machine learning and security.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "Oracle",
        "slug":        "oracle",
        "description": "Database, cloud infrastructure and Java certifications from Oracle.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "Databricks",
        "slug":        "databricks",
        "description": "Data engineering and machine learning certifications on the Databricks Lakehouse Platform.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    # -- Networking ----------------------------------------------------------
    {
        "name":        "Cisco",
        "slug":        "cisco",
        "description": "Networking, security and collaboration certifications from CCNA to CCIE.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "Snowflake",
        "slug":        "snowflake",
        "description": "Data platform certifications covering data engineering, architecture and administration.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    # -- Vendor-neutral IT ---------------------------------------------------
    {
        "name":        "CompTIA",
        "slug":        "comptia",
        "description": "Vendor-neutral IT certifications covering networking, security, cloud and project management.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "(ISC)2",
        "slug":        "isc2",
        "description": "Globally recognised security certifications including CISSP, CCSP and SSCP.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "ISACA",
        "slug":        "isaca",
        "description": "IT governance and audit certifications including CISA, CISM and CRISC.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "EC-Council",
        "slug":        "ec-council",
        "description": "Ethical hacking and cybersecurity certifications including CEH and CHFI.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    # -- Project & Service Management ----------------------------------------
    {
        "name":        "PMI",
        "slug":        "pmi",
        "description": "Project management certifications including PMP, PMI-ACP and CAPM.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "ITIL",
        "slug":        "axelos",
        "description": "ITIL and PRINCE2 certifications for IT service management and project delivery.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    # -- Virtualisation & DevOps ---------------------------------------------
    {
        "name":        "VMware",
        "slug":        "vmware",
        "description": "Virtualisation and multi-cloud certifications from VCP to VCDX.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "HashiCorp",
        "slug":        "hashicorp",
        "description": "Infrastructure-as-code certifications for Terraform, Vault, Consul and Nomad.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "Linux Foundation",
        "slug":        "linux-foundation",
        "description": "Open-source certifications including CKA, CKAD, CKS and LFCS.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    # -- Data & AI -----------------------------------------------------------
    {
        "name":        "NVIDIA",
        "slug":        "nvidia",
        "description": "AI and data engineering certifications for NVIDIA GPUs and accelerators.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "Python",
        "slug":        "python",
        "description": "Python programming certifications including Python 3, Data Science and Machine Learning.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "Fortinet",
        "slug":        "fortinet",
        "description": "Network security certifications including Fortinet NSE and Fortinet Security Specialist.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "Palo Alto Networks",
        "slug":        "palo-alto-networks",
        "description": "Network security certifications including Palo Alto Networks NSE and Palo Alto Networks Security Specialist.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  True,
    },
    {
        "name":        "Scrum",
        "slug":        "scrum",
        "description": "Scrum certifications including Scrum Master and Scrum Product Owner.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "Splunk",
        "slug":        "splunk",
        "description": "Splunk certifications including Splunk Certified Administrator and Splunk Certified Engineer.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "UIPath",
        "slug":        "uipath",
        "description": "RPA certifications including UIPath Certified RPA Developer and UIPath Certified RPA Professional.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "Salesforce",
        "slug":        "salesforce",
        "description": "CRM, platform developer and AI certifications across the Salesforce ecosystem.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    },
    {
        "name":        "Servicenow",
        "slug":        "servicenow",
        "description": "Servicenow certifications including Servicenow Certified Administrator and Servicenow Certified Developer.",
        "logo_url":    None,
        "is_active":   True,
        "is_popular":  False,
    }
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def get_existing_slugs(session: Session) -> set[str]:
    return {v.slug for v in session.exec(select(Vendor)).all()}


def seed_vendors(reset: bool = False, dry_run: bool = False) -> None:
    with Session(engine) as session:
        if reset:
            existing = session.exec(select(Vendor)).all()
            if dry_run:
                print(f"[dry-run] Would delete {len(existing)} vendor(s).")
            else:
                for v in existing:
                    session.delete(v)
                session.commit()
                print(f"  Deleted {len(existing)} existing vendor(s).")

        existing_slugs = get_existing_slugs(session)
        to_insert = [v for v in VENDORS if v["slug"] not in existing_slugs]
        skipped   = [v for v in VENDORS if v["slug"] in existing_slugs]

        if skipped and not reset:
            print(f"  Skipping {len(skipped)} already-existing vendor(s): "
                  + ", ".join(v["slug"] for v in skipped))

        if not to_insert:
            print("Nothing to insert - all vendors already present.")
            return

        if dry_run:
            print(f"[dry-run] Would insert {len(to_insert)} vendor(s):")
            for v in to_insert:
                pop = " [popular]" if v["is_popular"] else ""
                print(f"    {v['slug']:<25} {v['name']}{pop}")
            return

        for data in to_insert:
            session.add(Vendor(**data))

        session.commit()
        print(f"  Inserted {len(to_insert)} vendor(s):")
        for v in to_insert:
            pop = " [popular]" if v["is_popular"] else ""
            print(f"    + {v['slug']:<25} {v['name']}{pop}")

    print("\nVendor seed complete.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed vendors into testmaker DB.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing vendors before inserting (DESTRUCTIVE).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without touching the database.",
    )
    args = parser.parse_args()

    if args.reset and not args.dry_run:
        confirm = input(
            "WARNING: --reset will delete ALL vendors (and cascade to exams). "
            "Type 'yes' to continue: "
        )
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    seed_vendors(reset=args.reset, dry_run=args.dry_run)
