# 📊 Customer Churn & Revenue Optimization Intelligence System  
**End-to-End Data Science + Machine Learning + DevOps + Web Application**

> **Status:** 🚧 In Development |

A production-oriented decision intelligence system that predicts customer churn, quantifies revenue risk, and empowers business users. This project demonstrates a full lifecycle from raw data to deployed application, with ongoing enhancements for cloud and BI integration.

---

## 🔍 Problem Statement

Customer churn directly impacts revenue, but most organizations detect it **after** the loss occurs. This system answers three critical business questions:
1. **Who is likely to churn next?**  
2. **How much revenue is at risk due to churn?**  
3. **Which customers should be prioritized for retention?**

---

## 🎯 Solution Architecture

The system operates as a full-stack data product:
1. **ML Pipeline:** Ingests and processes data to train a predictive model.
2. **Inference Engine:** Generates churn probabilities and risk buckets for new customers.
3. **Database Layer:** Persists insights into a MySQL database for structured access.
4. **API Layer:** fastAPI backend serving real-time insights.
5. **Intelligence Dashboard:** Interactive frontend for business stakeholders.

### Key Outputs
- **Churn Probability:** 0–100% risk score per customer.
- **Risk Segmentation:** Low / Medium / High risk buckets.
- **Revenue at Risk:** Quantified financial impact ($).
- **Priority Score:** Ranking metric to guide retention efforts.

---

## � Current Progress & Features

### ✅ Completed Modules
- [x] **Data Pipeline**: Ingestion, Cleaning, and Feature Engineering.
- [x] **Machine Learning**: Model training (Random Forest) and Evaluation.
- [x] **Database Integration**: MySQL storage for predictions and KPIs.
- [x] **API Development**: FastAPI backend for real-time inference.
- [x] **Web Dashboard**: Interactive HTML/CSS/JS frontend.
- [x] **Containerization**: Docker support for the API/Webapp.

### 🚧 Roadmap (Upcoming)
- [ ] **Cloud Deployment (AWS):** Deploying the application to AWS EC2/ECS.
- [ ] **Business Intelligence**: Integration with **PowerBI** for advanced reporting.
- [ ] **Advanced DevOps**:
    - CI/CD Pipelines (GitHub Actions) enhancements.
    - Infrastructure as Code (Terraform).
    - Monitoring (Prometheus/Grafana).

---

## 📁 Project Structure

```text
DS-ML-DevOps/  
├── .github/workflows/    # CI/CD Pipelines
├── api/                  # Main Inference API
│   └── app.py            
├── data/                 # Raw and Processed Data
├── models/               # Serialized Models (pkl)
├── src/                  # Source Code
│   ├── webapp/           # Dashboard & Backend
│   │   ├── static/       # Frontend Assets
│   │   └── main.py       # Dashboard API
│   ├── business_insights.py
│   ├── ingestion.py
│   ├── persist_insights.py
│   └── train.py
├── Dockerfile            # Containerization
├── requirements.txt      # Dependencies
└── README.md             # Documentation
```

---

## 🧪 How to Run Locally

### Prerequisites
- Python 3.11+
- MySQL Server (running locally)

### 1. Setup Environment
```bash
pip install -r requirements.txt
pip install -r src/webapp/requirements.txt
```

### 2. Run the ML Pipeline
```bash
# Ingest, Clean, Train, and Persist Data
python src/ingestion.py
python src/train.py
python src/persist_insights.py
```

### 3. Start the Web Application
```bash
python -m uvicorn src.webapp.main:app --port 8000 --reload
```
Access the dashboard at: **http://127.0.0.1:8000/static/index.html**

---

## 💡 Why This Project?

- **Real Business Value:** Moves beyond accuracy metrics to financial impact.
- **Full-Stack Data Science:** Covers the entire lifecycle from data extraction to user-facing dashboard.
- **Scalable Design:** Built with microservices and containerization in mind.
