from fastapi import FastAPI, HTTPException
import sqlite3
# to initialize FastAPI App
app = FastAPI(title="Anonymized Patient Records API")

DB_PATH = "anonymized_patients (1).db"

@app.get("/patients/risk_alerts")
def get_risk_alerts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients")
    data = cursor.fetchall()
    conn.close()

    if not data:
        return {"message": "No patient data available."}

    keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
            "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]

    patients = [dict(zip(keys, row)) for row in data]

    # Risk Alert Logic
    for patient in patients:
        risk_score = 0
        conditions = []

        if "cyst" in patient["brain"].lower():
            risk_score += 20
            conditions.append("Brain cyst detected")
        if "defect" in patient["heart"].lower():
            risk_score += 30
            conditions.append("Heart defect found")
        if "spina bifida" in patient["spine"].lower():
            risk_score += 25
            conditions.append("Spinal issue detected")
        if patient["BMI"] and (patient["BMI"] > 30 or patient["BMI"] < 18):
            risk_score += 15
            conditions.append("BMI outside normal range")
        if "abnormal" in patient["abdominal_wall"].lower():
            risk_score += 10
            conditions.append("Abnormal abdominal structure")

        # Determine Risk Level
        if risk_score >= 50:
            patient["risk_level"] = "High"
        elif risk_score >= 20:
            patient["risk_level"] = "Moderate"
        else:
            patient["risk_level"] = "Low"

        patient["risk_conditions"] = conditions

    return {"total_patients": len(patients), "data": patients}

@app.get("/patients/trends")
def get_health_trends():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # to get BMI trends
    cursor.execute("SELECT demographic_age, AVG(BMI), COUNT(*) FROM patients GROUP BY demographic_age ORDER BY demographic_age")
    bmi_trends = cursor.fetchall()

    # to get disease frequency trends
    cursor.execute("SELECT COUNT(*) AS frequency, brain FROM patients WHERE brain != 'Not Reported' GROUP BY brain ORDER BY frequency DESC")
    brain_disease_trends = cursor.fetchall()

    conn.close()

    return {
        "BMI_trends": [{"age": age, "avg_BMI": round(bmi, 2), "count": count} for age, bmi, count in bmi_trends],
        "Brain_disease_trends": [{"disease": disease, "frequency": freq} for freq, disease in brain_disease_trends]
    }

@app.get("/patients/predict_risk")
def predict_future_risk():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # to fetch patients with borderline risk conditions
    cursor.execute("""
        SELECT * FROM patients
        WHERE brain LIKE '%mild cyst%' OR heart LIKE '%minor defect%' OR
        spine LIKE '%slight curvature%' OR BMI > 28 OR BMI < 20
    """)
    data = cursor.fetchall()
    conn.close()

    if not data:
        return {"message": "No borderline risk patients found."}

    keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
            "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]

    patients = [dict(zip(keys, row)) for row in data]

    return {"total_risk_patients": len(patients), "data": patients}

# to calculate AI-Powered Patient Risk Score
@app.get("/patients/risk_score/{patient_id}")
def calculate_risk_score(patient_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Patient not found.")

    keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
            "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]
    patient = dict(zip(keys, row))

    # AI-Powered Risk Score Logic
    risk_score = 0
    if "cyst" in patient["brain"].lower():
        risk_score += 20
    if "defect" in patient["heart"].lower():
        risk_score += 30
    if "spina bifida" in patient["spine"].lower():
        risk_score += 25
    if patient["BMI"] and (patient["BMI"] > 30 or patient["BMI"] < 18):
        risk_score += 15
    if "abnormal" in patient["abdominal_wall"].lower():
        risk_score += 10

    return {"patient_id": patient_id, "risk_score": min(100, risk_score)}

# to search patients by medical condition
@app.get("/patients/search_condition")
def search_by_condition(condition: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT * FROM patients WHERE
        LOWER(head) LIKE ? OR LOWER(brain) LIKE ? OR LOWER(heart) LIKE ? OR
        LOWER(spine) LIKE ? OR LOWER(abdominal_wall) LIKE ? OR LOWER(urinary_tract) LIKE ? OR
        LOWER(extremities) LIKE ?
    """
    params = tuple([f"%{condition.lower()}%"] * 7)
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()

    if not data:
        return {"message": f"No patients found with the condition: {condition}"}

    keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
            "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]

    patients = [dict(zip(keys, row)) for row in data]
    return {"total_matches": len(patients), "data": patients}

# to identify patients with high-risk conditions based on findings
@app.get("/patients/high_risk")
def get_high_risk_patients():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT * FROM patients WHERE
        brain LIKE '%cyst%' OR heart LIKE '%defect%' OR spine LIKE '%spina bifida%'
        OR BMI > 30 OR BMI < 18 OR gestational_age LIKE '2w%' OR gestational_age LIKE '4w%'
    """
    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()

    if not data:
        return {"message": "No high-risk patients found."}

    keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
            "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]

    patients = [dict(zip(keys, row)) for row in data]
    return {"total_high_risk_patients": len(patients), "data": patients}

# creating a filter to extract records based on specific value match
@app.get("/patients/filter")
def filter_patients(age: int = None, bmi: float = None, gender: str = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # constructing a dynamic query to handle all the cases
        query = "SELECT * FROM patients WHERE 1=1"
        params = []

        if age is not None:
            query += " AND demographic_age = ?"
            params.append(age)
        if bmi is not None:
            query += " AND BMI = ?"
            params.append(bmi)
        if gender:
            query += " AND gender = ?"
            params.append(gender)

        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()

        keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
                "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]
        patients = [dict(zip(keys, row)) for row in data]

        return {"total_filtered_patients": len(patients), "data": patients}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during filtering: {e}")

# to fetch all patients details
@app.get("/patients")
def get_all_patients():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients")
    data = cursor.fetchall()
    conn.close()

    if not data:
        raise HTTPException(status_code=404, detail="No patient records found.")

    keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
            "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]

    patients = [dict(zip(keys, row)) for row in data]
    return {"total_patients": len(patients), "data": patients}

# to get summary statistics of patient demographics
@app.get("/patients/stats")
def get_patient_statistics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT AVG(demographic_age), MIN(demographic_age), MAX(demographic_age), COUNT(*) FROM patients WHERE demographic_age IS NOT NULL")
    age_stats = cursor.fetchone() or (0, 0, 0, 0)

    cursor.execute("SELECT AVG(BMI), MIN(BMI), MAX(BMI) FROM patients WHERE BMI IS NOT NULL")
    bmi_stats = cursor.fetchone() or (0, 0, 0)

    cursor.execute("SELECT gender, COUNT(*) FROM patients WHERE gender IS NOT NULL GROUP BY gender")
    gender_distribution = cursor.fetchall()

    conn.close()

    return {
        "total_patients": age_stats[3],
        "age": {"average": round(age_stats[0], 2), "min": age_stats[1], "max": age_stats[2]},
        "BMI": {"average": round(bmi_stats[0], 2), "min": bmi_stats[1], "max": bmi_stats[2]},
        "gender_distribution": {gender: count for gender, count in gender_distribution}
    }


# to fetch a specific patient by ID
@app.get("/patients/{patient_id}")
def get_patient_by_id(patient_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Patient not found.")

    keys = ["patient_id", "demographic_age", "gestational_age", "gender", "BMI",
            "head", "brain", "heart", "spine", "abdominal_wall", "urinary_tract", "extremities", "conclusion"]

    return dict(zip(keys, row))
