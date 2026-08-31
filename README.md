AI Sales Agent

An AI-powered sales automation platform that helps sales teams manage customer enquiries, analyze email conversations, detect sales opportunities, generate quotations, create Gmail drafts, and answer business questions using a Retrieval-Augmented Generation (RAG) knowledge base.



Live Demo

Production Application:

https://agent.truefoxaiinc.com

Demo credentials are shared privately with authorized reviewers and are not stored in this repository.



Overview

AI Sales Agent is designed to automate repetitive sales activities while keeping important business decisions grounded in company data.

The application combines:

AI-assisted email analysis

Gmail integration

Sales opportunity detection

RFQ requirement extraction

Customer and product management

Automated quotation generation

PDF quotation generation

Gmail draft creation

Retrieval-Augmented Generation (RAG)

Company knowledge-base search

Secure authentication

Production deployment with HTTPS


The system provides an end-to-end workflow from receiving a customer enquiry to preparing a quotation and email response.

Key Features :

AI Inbox

Connect Gmail and synchronize customer conversations into the application.

The AI Inbox supports:

- Gmail OAuth integration

- Email synchronization

- Conversation/thread viewing

- AI thread summarization

- AI-generated reply suggestions

- Sales opportunity detection

- RFQ analysis

- Quotation requirement extraction



AI Reply Suggestions

The application analyzes customer conversations and generates context-aware sales replies.

AI responses are designed to avoid inventing unsupported business information such as:

- Product prices

- Availability

- Delivery commitments

- Payment terms

- Warranty information

When information is unavailable, the system requests confirmation or human review.


Sales Opportunity Detection

Email conversations can automatically be analyzed for potential sales opportunities.

The system identifies signals such as:

- Pricing requests

- Purchase intent

- Product enquiries

- Availability requests

- Delivery requirements

- Order discussions

- Quotation requests


RFQ / Quotation Requirement Extraction

Customer RFQs can be converted into structured quotation requirements.

The AI can identify:

- Product

- Quantity

- Pricing requirement

- Availability requirement

- Delivery requirement

- Payment-term requirement

- Extraction confidence


Customer Management

Manage customer information through the web application.

Features include:

- Create customers

- View customers

- Update customer information

- Maintain customer contact details

- Track active customer records


Product Management

Maintain the products and services used during quotation generation.

Product information can include:

- SKU

- Product/service name

- Unit

- Unit price

- Currency

- Tax rate

- Active status



Quotation Management

Create structured sales quotations using customer and product information.

Features include:

- Manual quotation creation

- AI-assisted quotation creation from RFQs

- Quotation preview

- Automatic quotation numbering

- Draft/review workflow

- Price calculations

- Tax calculations

- Quotation history


Example workflow:

Customer RFQ

→ AI Requirement Extraction

→ Quotation Preview

→ Quotation Creation

→ PDF Generation


PDF Quotation Generation

Quotations can be exported as professional PDF documents containing:

- Quotation number

- Customer details

- Issue date

- Expiry date

- Products/services

- Quantity

- Unit price

- Subtotal

- Tax

- Total amount

- Notes

- Terms


Gmail Draft Automation

After creating a quotation, the application can prepare a Gmail draft for the salesperson.

The workflow supports:

1. Generate quotation

2. Generate PDF

3. Create Gmail reply draft

4. Attach quotation PDF

5. Allow salesperson to review before sending

The application intentionally keeps the final email-send decision under human control.



Knowledge Base & RAG

The application includes a Retrieval-Augmented Generation knowledge base.

Business documents can be uploaded and used as context for AI-generated answers.

Knowledge Base capabilities

- Upload business knowledge

- Store processed documents

- Search relevant content

- Retrieve supporting context

- Generate grounded AI answers

- Display the source used for the answer


Example:

Question

> What services do we offer and what is the price?

The system retrieves relevant company information before generating its response.

This reduces unsupported AI answers and keeps responses grounded in available business knowledge.



End-to-End Sales Workflow

text

Customer sends RFQ email

       ↓

Gmail synchronization

       ↓

AI Inbox

      ↓

Thread summarization

      ↓

AI reply suggestions

       ↓

Sales opportunity detection

       ↓

Quotation requirement extraction

       ↓

Customer / Product matching

       ↓

Quotation preview

       ↓

Quotation creation

       ↓

PDF generation

       ↓

Gmail draft + PDF attachment

       ↓

Salesperson reviews and sends


Architecture

text

                      ┌─────────────────────┐

                      │      Customer       │

                      └──────────┬──────────┘

                                 │

                                 ▼

                        ┌─────────────────────┐

                       │        Gmail        │

                        └──────────┬──────────┘

                                   │ OAuth / API

                                   ▼

┌─────────────────┐      ┌─────────────────────┐

│   React + Vite  │─────▶│       FastAPI       │

│    Frontend     │      │       Backend       │

└─────────────────┘      └──────────┬──────────┘

                               │

           ┌───────────────────┼───────────────────┐

               │                   │                   │

               ▼                   ▼                   ▼

       ┌──────────────┐    ┌──────────────┐    ┌──────────────┐

      │ PostgreSQL   │    │ Redis/Valkey │    │ OpenAI API   │

      └──────────────┘    └──────────────┘    └──────────────┘

                                   │

                                   ▼

                          ┌──────────────────┐

                          │ Knowledge Base   │

                          │      / RAG       │

                          └──────────────────┘



Technology Stack

Frontend

- React

- TypeScript

- Vite

- Axios

- Modern responsive web UI


Backend

- Python

- FastAPI

- Uvicorn

- SQLAlchemy

- Pydantic


AI

- OpenAI API

- AI-assisted email processing

- Retrieval-Augmented Generation (RAG)

- Grounded response generation


Data & Infrastructure

- PostgreSQL

- Redis / Valkey

- AWS EC2

- Nginx

- systemd

- Let's Encrypt / Certbot

- HTTPS


Integrations

- Gmail API

- Google OAuth 2.0

- OpenAI API



Project Structure

text

AI\_Sales\_Agent/

│

├── apps/

│   └── api/                 # FastAPI backend

│       ├── app/

│       │   ├── api/         # API routes

│       │   ├── services/    # Business \& AI services

│       │   ├── models/      # Database models

│       │   └── ...

│       └── ...

│

├── web/                     # React/Vite frontend

│   ├── src/

│   │   ├── api/

│   │   ├── components/

│   │   ├── pages/

│   │   └── ...

│   └── ...

│

├── storage/                 # Application storage

├── docker-compose.yml

├── .env.example

├── .gitignore

└── README.md


API Modules


The backend exposes APIs for:

- Authentication

- Customers

- Products

- Gmail OAuth

- Email synchronization

- Email threads

- AI summaries

- AI reply suggestions

- Sales opportunity detection

- RFQ extraction

- Quotations

- PDF generation

- Knowledge Base

- RAG search and answers

- Health monitoring


API documentation is available through FastAPI Swagger when enabled for the deployment.


Local Development

1. Clone the repository

git clone https://github.com/mukthaar917/AI\_Sales\_Agent.git

cd AI\_Sales\_Agent


2. Create environment configuration

Copy the example configuration:

cp .env.example .env


Configure the required environment variables locally.

Never commit .env or production credentials to Git.



3. Start infrastructure

If using Docker Compose:

docker compose up -d


4. Run the backend

cd apps/api

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload


5. Run the frontend

cd web

npm install

npm run dev



Environment Configuration

The application requires configuration for:

text

Application environment

Frontend URL

Backend URL

PostgreSQL

Redis

JWT authentication

Google OAuth

Gmail scopes

Token encryption

AI provider

AI model

AI API credentials

Use .env.example to document required variable names.

Security


Do not commit:

text

.env

API keys

OAuth client secrets

JWT secrets

Database passwords

Encryption keys

Access tokens

Refresh tokens

Production secrets should be managed using secure environment variables or a secrets-management service.


Production Deployment

The production architecture uses:

text

Internet

  ↓

HTTPS

  ↓

Nginx

  ↓

React SPA

  +

/api/ reverse proxy

  ↓

FastAPI / Uvicorn

  ↓

PostgreSQL + Redis

  ↓

OpenAI / Gmail APIs



The backend runs as a system service and Nginx acts as the public reverse proxy.

HTTPS is configured using Let's Encrypt.


Health Check

Production health can be verified using:

text

GET /health



Expected response:

json

{

 "status": "healthy",

 "application": "AI Sales Agent",

 "environment": "production"

}



Security Design

The application includes:

- JWT authentication

- Google OAuth 2.0

- Encrypted integration tokens

- Environment-based secrets

- HTTPS

- Nginx reverse proxy

- Restricted backend network exposure

- Human review before sending AI-generated sales emails

- Grounding rules for AI-generated business information


Demo Scenario

A typical demonstration uses a customer requesting a quotation for multiple laptops.


The application demonstrates:

1. Gmail receives the RFQ.

2. AI Sales Agent synchronizes the email.

3. AI summarizes the conversation.

4. AI generates a suggested response.

5. The system detects a sales opportunity.

6. AI extracts quotation requirements.

7. A quotation preview is generated.

8. The salesperson creates the quotation.

9. A PDF quotation is generated.

10. Gmail draft is created with the PDF attached.

11. The salesperson reviews the response before sending.

12. Knowledge Base RAG answers business questions using uploaded company information.



Current Status

Production deployment: Operational

Core workflows implemented:

- Authentication

- Customer management

- Product management

- Gmail OAuth integration

- Gmail synchronization

- AI Inbox

- AI thread summarization

- AI reply suggestions

- Sales opportunity detection

- RFQ requirement extraction

- Quotation preview

- Quotation generation

- PDF quotation generation

- Gmail draft creation

- Knowledge Base

- RAG-based AI answers

- Production deployment

- HTTPS configuration



Future Improvements

Potential future enhancements include:

- CRM integrations

- Automated lead scoring

- Sales analytics dashboard

- Multi-user roles and permissions

- Approval workflows

- Advanced quotation templates

- Inventory integration

- Automated follow-up scheduling

- Additional email providers

- Vector database integration

- AI evaluation and monitoring

- Audit logging



Repository

GitHub:

https://github.com/mukthaar917/AI\_Sales\_Agent

Primary development branch:

text

feature/rag-knowledge-base



Author

Muktha A R



AI Sales Agent — AI-powered sales workflow automation.

Disclaimer :

AI-generated sales responses and quotations should be reviewed by an authorized user before being sent to customers. Business-critical information such as pricing, availability, delivery commitments, payment terms, and contractual information should be verified against approved company data.

