from __future__ import annotations

DEPARTMENT_DATA = [
    ('Department of Computer Science', 'CS'),
    ('Department of Software Engineering', 'SE'),
    ('Department of Electrical Engineering', 'EE'),
    ('Department of Mechanical Engineering', 'ME'),
    ('Department of Civil Engineering', 'CE'),
    ('Department of Chemical Engineering', 'CHE'),
    ('Department of Biomedical Engineering', 'BME'),
    ('Department of Health and Medical Sciences', 'HMS'),
    ('Department of Pharmacy', 'PHARM'),
    ('Department of Management Sciences', 'MGT'),
    ('Department of Accounting and Finance', 'ACF'),
    ('Department of Economics', 'ECO'),
    ('Department of Psychology', 'PSY'),
    ('Department of Media and Communication', 'MCM'),
    ('Department of Law', 'LAW'),
    ('Department of Mathematics', 'MATH'),
    ('Department of Physics', 'PHY'),
    ('Department of Biotechnology', 'BIOTECH'),
    ('Department of Environmental Sciences', 'ENV'),
    ('Department of International Relations', 'IR'),
]

QUALIFICATIONS = {
    'pre_engineering': 'Intermediate in Pre-Engineering (FSc Pre-Engineering)',
    'ics': 'Intermediate in Computer Science (FSc ICS)',
    'pre_medical': 'Intermediate in Pre-Medical (FSc Pre-Medical)',
    'any': 'Intermediate (any discipline) or equivalent',
    'b_cs': "Bachelor's degree in Computer Science or a closely related field",
    'b_se_cs': "Bachelor's degree in Software Engineering or Computer Science",
    'b_ee': "Bachelor's degree in Electrical Engineering or a closely related field",
    'b_me': "Bachelor's degree in Mechanical Engineering or a closely related field",
    'b_civil': "Bachelor's degree in Civil Engineering or a closely related field",
    'b_econ': "Bachelor's degree in Economics or a closely related field",
    'b_psych': "Bachelor's degree in Psychology or a closely related field",
    'b_math': "Bachelor's degree in Mathematics or a closely related field",
    'b_biotech': "Bachelor's degree in Biotechnology or a closely related field",
    'b_env': "Bachelor's degree in Environmental Science or a closely related field",
    'b_ir': "Bachelor's degree in International Relations, Political Science, or a closely related field",
    'b_law': "Bachelor of Laws (LLB) degree",
    'b_any': "Bachelor's degree in any discipline",
}

TEST_TYPES = {
    'usat': 'University Sciences Admission Test (USAT)',
    'ecat': 'Engineering College Admission Test (ECAT)',
    'mdcat': 'Medical and Dental College Admission Test (MDCAT)',
    'lat': 'Law Admission Test (LAT)',
    'pist': 'PIST University Entry Test',
    'pist_grad': 'PIST University Entry Test (Graduate)',
    'gat': 'Graduate Assessment Test (GAT)',
    'nts': 'National Testing Service Test (NTS)',
}

QUALIFICATION_GROUP_CODES = {
    'pre_engineering': 'PRE_ENGINEERING',
    'ics': 'ICS',
    'pre_medical': 'PRE_MEDICAL',
    'any': 'ANY',
}


def p(code, name, department, qualification, percentage, tests, duration, degree, careers):
    return {
        'code': code, 'name': name, 'department': department, 'qualification': qualification,
        'percentage': percentage, 'tests': tests, 'duration': duration, 'degree': degree,
        'careers': careers,
    }


PROGRAM_DATA = [
    p('BSCS-ISB', 'Bachelor of Science in Computer Science', 'CS', ['pre_engineering', 'ics'], 60, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Software Engineer\nSystems Analyst\nBackend Developer\nFull-Stack Developer\nDatabase Administrator'),
    p('MSCS-ISB', 'Master of Science in Computer Science', 'CS', ['b_cs'], 60, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Research Associate\nSenior Software Engineer\nTechnical Lead'),
    p('BSSE-ISB', 'Bachelor of Science in Software Engineering', 'SE', ['pre_engineering', 'ics'], 60, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Software Engineer\nQuality Assurance Engineer\nDevOps Engineer\nProject Coordinator'),
    p('MSSE-ISB', 'Master of Science in Software Engineering', 'SE', ['b_se_cs'], 60, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Software Architect\nEngineering Manager'),
    p('BSAI-ISB', 'Bachelor of Science in Artificial Intelligence', 'CS', ['pre_engineering', 'ics'], 65, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Machine Learning Engineer\nData Scientist\nArtificial Intelligence Research Assistant\nComputer Vision Engineer'),
    p('BSDS-ISB', 'Bachelor of Science in Data Science', 'CS', ['pre_engineering', 'ics'], 60, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Data Analyst\nData Engineer\nBusiness Intelligence Analyst'),
    p('BSIT-ISB', 'Bachelor of Science in Information Technology', 'CS', ['pre_engineering', 'ics'], 55, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Network Administrator\nInformation Technology Support Engineer\nSystems Administrator\nWeb Developer'),
    p('BSCYS-ISB', 'Bachelor of Science in Cyber Security', 'CS', ['pre_engineering', 'ics'], 60, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Security Analyst\nPenetration Tester\nNetwork Security Engineer\nDigital Forensics Investigator'),
    p('BSEE-ISB', 'Bachelor of Science in Electrical Engineering', 'EE', ['pre_engineering'], 60, ['ecat', 'pist'], '4 Years', 'Undergraduate', 'Electrical Design Engineer\nPower Systems Engineer\nControl Systems Engineer'),
    p('BSELEC-ISB', 'Bachelor of Science in Electronics Engineering', 'EE', ['pre_engineering'], 60, ['ecat', 'pist'], '4 Years', 'Undergraduate', 'Electronics Design Engineer\nEmbedded Systems Engineer\nTelecommunications Engineer'),
    p('MSEE-ISB', 'Master of Science in Electrical Engineering', 'EE', ['b_ee'], 60, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Senior Power Systems Engineer\nResearch Engineer'),
    p('BSME-ISB', 'Bachelor of Science in Mechanical Engineering', 'ME', ['pre_engineering'], 60, ['ecat', 'pist'], '4 Years', 'Undergraduate', 'Mechanical Design Engineer\nManufacturing Engineer\nHeating Ventilation and Air Conditioning Engineer'),
    p('MSME-ISB', 'Master of Science in Mechanical Engineering', 'ME', ['b_me'], 60, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Senior Design Engineer\nResearch Engineer'),
    p('BSCE-ISB', 'Bachelor of Science in Civil Engineering', 'CE', ['pre_engineering'], 60, ['ecat', 'pist'], '4 Years', 'Undergraduate', 'Structural Engineer\nSite Engineer\nConstruction Project Manager'),
    p('MSCE-ISB', 'Master of Science in Civil Engineering', 'CE', ['b_civil'], 60, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Senior Structural Engineer\nInfrastructure Consultant'),
    p('BSCHE-ISB', 'Bachelor of Science in Chemical Engineering', 'CHE', ['pre_engineering'], 60, ['ecat', 'pist'], '4 Years', 'Undergraduate', 'Process Engineer\nPlant Engineer\nQuality Control Engineer'),
    p('BSBME-ISB', 'Bachelor of Science in Biomedical Engineering', 'BME', ['pre_engineering', 'pre_medical'], 60, ['ecat', 'pist'], '4 Years', 'Undergraduate', 'Biomedical Equipment Engineer\nClinical Engineer\nMedical Device Developer'),
    p('MBBS-ISB', 'Doctor of Medicine (Bachelor of Medicine, Bachelor of Surgery — MBBS)', 'HMS', ['pre_medical'], 70, ['mdcat'], '5 Years', 'Undergraduate', 'Medical Officer\nHouse Officer\nGeneral Physician (post-licensure)'),
    p('BSN-ISB', 'Bachelor of Science in Nursing', 'HMS', ['pre_medical'], 60, ['pist'], '4 Years', 'Undergraduate', 'Registered Nurse\nClinical Nurse Specialist\nNurse Educator'),
    p('PHARMD-ISB', 'Doctor of Pharmacy (PharmD)', 'PHARM', ['pre_medical', 'pre_engineering'], 65, ['mdcat', 'pist'], '5 Years', 'Undergraduate', 'Clinical Pharmacist\nHospital Pharmacist\nPharmaceutical Researcher\nDrug Regulatory Affairs Officer'),
    p('BBA-ISB', 'Bachelor of Business Administration (BBA)', 'MGT', ['any'], 50, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Management Trainee\nMarketing Executive\nHuman Resources Officer\nOperations Coordinator'),
    p('MBA-ISB', 'Master of Business Administration (MBA)', 'MGT', ['b_any'], 50, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Business Development Manager\nProduct Manager\nManagement Consultant'),
    p('BSAF-ISB', 'Bachelor of Science in Accounting and Finance', 'ACF', ['any'], 55, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Financial Analyst\nAccountant\nAuditor\nInvestment Analyst'),
    p('BSBF-ISB', 'Bachelor of Science in Banking and Finance', 'ACF', ['any'], 55, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Banking Officer\nCredit Analyst\nRisk Analyst'),
    p('BSECO-ISB', 'Bachelor of Science in Economics', 'ECO', ['any'], 55, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Economic Analyst\nPolicy Research Assistant\nData Analyst'),
    p('MSECO-ISB', 'Master of Science in Economics', 'ECO', ['b_econ'], 55, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Economic Consultant\nResearch Economist'),
    p('BSPSY-ISB', 'Bachelor of Science in Psychology', 'PSY', ['any'], 55, ['pist'], '4 Years', 'Undergraduate', 'Clinical Psychology Assistant\nHuman Resources Officer\nResearch Assistant'),
    p('MSPSY-ISB', 'Master of Science in Psychology', 'PSY', ['b_psych'], 55, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Clinical Psychologist (post-licensure)\nCounselor'),
    p('BSMASS-ISB', 'Bachelor of Science in Mass Communication', 'MCM', ['any'], 50, ['pist'], '4 Years', 'Undergraduate', 'Journalist\nContent Producer\nPublic Relations Officer\nBroadcast Reporter'),
    p('BSMEDIA-ISB', 'Bachelor of Science in Media Studies', 'MCM', ['any'], 50, ['pist'], '4 Years', 'Undergraduate', 'Digital Media Strategist\nVideo Producer\nSocial Media Manager'),
    p('LLB-ISB', 'Bachelor of Laws (LLB)', 'LAW', ['any'], 60, ['lat'], '5 Years', 'Undergraduate', 'Advocate (post-bar)\nLegal Associate\nLegal Researcher\nCorporate Legal Advisor'),
    p('LLM-ISB', 'Master of Laws (LLM)', 'LAW', ['b_law'], 55, ['pist_grad'], '1.5 Years', 'Graduate (Masters)', 'Senior Legal Consultant\nLitigation Specialist'),
    p('BSMATH-ISB', 'Bachelor of Science in Mathematics', 'MATH', ['pre_engineering'], 60, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Data Analyst\nActuarial Analyst\nStatistician\nMathematics Instructor'),
    p('MSMATH-ISB', 'Master of Science in Mathematics', 'MATH', ['b_math'], 55, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Research Analyst\nQuantitative Analyst'),
    p('BSPHY-ISB', 'Bachelor of Science in Physics', 'PHY', ['pre_engineering'], 60, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Research Assistant\nLaboratory Technologist\nPhysics Instructor'),
    p('BSBIOTECH-ISB', 'Bachelor of Science in Biotechnology', 'BIOTECH', ['pre_medical'], 60, ['usat', 'pist'], '4 Years', 'Undergraduate', 'Biotechnology Research Assistant\nQuality Control Analyst\nLaboratory Technologist'),
    p('MSBIOTECH-ISB', 'Master of Science in Biotechnology', 'BIOTECH', ['b_biotech'], 55, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Research Scientist\nProduct Development Specialist'),
    p('BSES-ISB', 'Bachelor of Science in Environmental Science', 'ENV', ['pre_medical', 'pre_engineering'], 55, ['pist'], '4 Years', 'Undergraduate', 'Environmental Analyst\nSustainability Officer\nEnvironmental Impact Assessment Consultant'),
    p('MSES-ISB', 'Master of Science in Environmental Science', 'ENV', ['b_env'], 55, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Environmental Compliance Manager\nPolicy Researcher'),
    p('BSIR-ISB', 'Bachelor of Science in International Relations', 'IR', ['any'], 55, ['pist'], '4 Years', 'Undergraduate', 'Foreign Service Assistant\nPolicy Research Analyst\nDiplomatic Affairs Officer'),
    p('MSIR-ISB', 'Master of Science in International Relations', 'IR', ['b_ir'], 55, ['pist_grad'], '2 Years', 'Graduate (Masters)', 'Foreign Policy Analyst\nInternational Development Consultant'),
]

MIRRORED_CODES = {
    'BSCS-ISB': 'BSCS', 'BSSE-ISB': 'BSSE', 'BSAI-ISB': 'BSAI', 'BSEE-ISB': 'BSEE',
    'BBA-ISB': 'BBA', 'BSAF-ISB': 'BSAF', 'LLB-ISB': 'LLB',
}
