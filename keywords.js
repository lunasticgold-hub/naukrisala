/* ============ NAUKRISALA — shared keyword dictionary ============
   Single source of truth for the AI tools (Resume Evaluator, Skill Gap
   Planner). The KEYWORDS array below is a verbatim copy of the dictionary
   in apply.html (the Apply Assistant) so every tool agrees on terms.
   Track groupings only classify those same terms — no new skills are
   invented here. */

const KEYWORDS = [
  // AML / KYC / financial crime
  'AML','KYC','Know Your Customer','Anti-Money Laundering','Money Laundering','Transaction Monitoring',
  'Sanctions','Sanctions Screening','Sanctions List','PEP Screening','Politically Exposed Person',
  'EDD','Enhanced Due Diligence','CDD','Customer Due Diligence','Due Diligence','KYC Verification',
  'Suspicious Activity Report','Suspicious Transaction Report','AML Compliance','Financial Crime',
  'Fraud Detection','Fraud Prevention','Risk Assessment','Customer Risk Assessment','Risk Rating',
  'Name Screening','Watchlist Screening','Client Screening','Screening','Adverse Media','Negative News Screening',
  'Correspondent Banking','Trade Surveillance','Market Surveillance','Compliance Monitoring',
  'Regulatory Compliance','Regulatory Reporting','KYC Onboarding','Client Onboarding','Customer Onboarding',
  'Periodic Review','Remediation','Alert Management','Case Management','Investigations','Forensic',
  'AML Operations','KYC Operations','OFAC','FATF','RBI Guidelines','SEBI','Basel','AML Audit',
  'Beneficial Ownership','Ultimate Beneficial Owner','UBO','Source of Funds','Source of Wealth',
  'Transaction Analysis','Payment Screening','World-Check','Actimize','Mantas','Fircosoft','LexisNexis',
  'Refinitiv','Onboarding','Quality Assurance','Quality Control','Compliance','Risk Management',
  // general tech / ops / other tracks
  'SQL','Excel','Advanced Excel','VBA','Macros','Python','Power BI','Power Query','Tableau',
  'ServiceNow','Workday','SAP','SAP FICO','Java','Spring Boot','JavaScript','React','Angular','HTML','CSS',
  'Manual Testing','Automation Testing','Selenium','API Testing','Testing','Reconciliation','Settlements',
  'Trade Settlement','Corporate Actions','SWIFT','Payments','Payment Processing','UPI','NEFT','RTGS',
  'Card Operations','Loan Operations','Credit Analysis','Underwriting','Data Analysis','Data Entry',
  'MIS Reporting','MS Office','Stakeholder Management','Process Improvement','SLA','SOP','Documentation',
  'Internal Audit','Audit','Back Office','Middle Office','Investment Banking Operations','Custody',
  'Fund Accounting','Derivatives','Equities','Fixed Income','FX','Treasury','Operations',
  'Machine Learning','Data Science','ETL','Data Warehouse','Business Intelligence','Communication Skills'
];
const kwRegex = term => {
  const e = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp('(?<![a-z0-9])' + e + '(?![a-z0-9])', 'gi');
};
const KW = KEYWORDS.map(t => ({ term: t, lower: t.toLowerCase(), re: kwRegex(t) }));

function findKeywords(text) {
  const found = [];
  for (const k of KW) {
    k.re.lastIndex = 0;
    const m = String(text || '').match(k.re);
    if (m) found.push({ term: k.term, lower: k.lower, count: m.length });
  }
  const kept = found.filter(f => !found.some(o => o !== f && o.lower.includes(f.lower)));
  kept.sort((a, b) => b.count - a.count || KW.findIndex(k => k.lower === a.lower) - KW.findIndex(k => k.lower === b.lower));
  return kept;
}
function textHas(text, lower) {
  const k = KW.find(x => x.lower === lower);
  if (!k) return false;
  k.re.lastIndex = 0;
  return k.re.test(String(text || ''));
}

/* The 15 NaukriSala tracks — slugs and labels as used by jobs.json. */
const TRACKS = [
  { slug: 'aml-kyc', label: 'AML & KYC Analyst' },
  { slug: 'servicenow', label: 'ServiceNow Developer' },
  { slug: 'data-science-ai', label: 'Data Science & AI Engineering' },
  { slug: 'stom', label: 'STOM — Service Transition & Ops' },
  { slug: 'power-bi', label: 'Power BI Developer' },
  { slug: 'data-analyst', label: 'Data Analyst' },
  { slug: 'workday', label: 'Workday Consultant' },
  { slug: 'python-fullstack', label: 'Full Stack Python' },
  { slug: 'java-fullstack', label: 'Full Stack Java Developer' },
  { slug: 'qa-testing', label: 'Software Testing (QA)' },
  { slug: 'ib-operations', label: 'Investment Banking Operations' },
  { slug: 'sap-fico', label: 'SAP FICO (S/4HANA Finance)' },
  { slug: 'web-dev', label: 'Web Development' },
  { slug: 'dotnet', label: '.NET Developer' },
  { slug: 'dbi', label: 'Database & Business Intelligence' }
];

/* Per-track keyword sets — every term below exists in KEYWORDS above.
   Used for the Evaluator's skills-match score. */
const TRACK_KW = {
  'aml-kyc': ['AML','KYC','Know Your Customer','Anti-Money Laundering','Transaction Monitoring','Sanctions Screening','PEP Screening','EDD','Enhanced Due Diligence','CDD','Customer Due Diligence','KYC Verification','Suspicious Activity Report','Suspicious Transaction Report','AML Compliance','Financial Crime','Fraud Detection','Risk Assessment','Risk Rating','Name Screening','Watchlist Screening','Adverse Media','Negative News Screening','Regulatory Compliance','Regulatory Reporting','KYC Onboarding','Client Onboarding','Periodic Review','Remediation','Alert Management','Case Management','Investigations','OFAC','FATF','RBI Guidelines','Beneficial Ownership','Ultimate Beneficial Owner','Source of Funds','Source of Wealth','Transaction Analysis','Payment Screening','World-Check','Actimize','LexisNexis','Quality Assurance','Compliance','Risk Management','Excel'],
  'servicenow': ['ServiceNow','JavaScript','SLA','Process Improvement','Documentation','Stakeholder Management','Communication Skills','Excel'],
  'data-science-ai': ['Python','Machine Learning','Data Science','SQL','ETL','Data Warehouse','Data Analysis','Power BI','Tableau','Excel','Business Intelligence'],
  'stom': ['ServiceNow','SLA','SOP','Process Improvement','Stakeholder Management','Documentation','Communication Skills','MS Office','Excel'],
  'power-bi': ['Power BI','Power Query','SQL','Excel','Advanced Excel','Data Analysis','MIS Reporting','Tableau','Business Intelligence','ETL'],
  'data-analyst': ['Data Analysis','SQL','Excel','Advanced Excel','Power BI','Power Query','Tableau','Python','MIS Reporting','VBA','Macros','Business Intelligence'],
  'workday': ['Workday','Excel','MS Office','Data Analysis','Stakeholder Management','Documentation','Communication Skills'],
  'python-fullstack': ['Python','JavaScript','React','HTML','CSS','SQL','API Testing','ETL'],
  'java-fullstack': ['Java','Spring Boot','JavaScript','React','Angular','HTML','CSS','SQL','API Testing'],
  'qa-testing': ['Manual Testing','Automation Testing','Selenium','API Testing','Testing','SQL','Documentation','SOP','Quality Assurance','Quality Control'],
  'ib-operations': ['Investment Banking Operations','Settlements','Trade Settlement','Corporate Actions','SWIFT','Reconciliation','Custody','Fund Accounting','Derivatives','Equities','Fixed Income','FX','Treasury','Back Office','Middle Office','Payments','KYC','Excel'],
  'sap-fico': ['SAP','SAP FICO','Reconciliation','Internal Audit','Audit','Excel','Advanced Excel','Data Analysis','MS Office','Fund Accounting'],
  'web-dev': ['HTML','CSS','JavaScript','React','Angular','Python','SQL'],
  'dotnet': ['SQL','JavaScript','HTML','CSS','API Testing','Testing','Documentation'],
  'dbi': ['SQL','ETL','Data Warehouse','Business Intelligence','Power BI','Power Query','Tableau','Data Analysis','MIS Reporting','Excel','Advanced Excel']
};

/* Skill Gap Planner checklists — grouped subsets of TRACK_KW. */
const SKILL_GROUPS = {
  'aml-kyc': [
    ['KYC & due diligence', ['KYC','CDD','EDD','KYC Onboarding','Beneficial Ownership','Source of Funds','Periodic Review']],
    ['Screening', ['Sanctions Screening','Name Screening','PEP Screening','Adverse Media','Payment Screening']],
    ['Monitoring, alerts & reporting', ['Transaction Monitoring','Alert Management','Case Management','Investigations','Suspicious Transaction Report','Suspicious Activity Report']],
    ['Compliance, risk & tools', ['AML Compliance','Regulatory Compliance','Risk Rating','Fraud Detection','World-Check','Actimize','Excel']]
  ],
  'servicenow': [
    ['Core skills', ['ServiceNow','JavaScript','SLA','Process Improvement','Documentation','Stakeholder Management','Communication Skills','Excel']]
  ],
  'data-science-ai': [
    ['Core skills', ['Python','Machine Learning','Data Science','SQL','Data Analysis']],
    ['Data & BI tooling', ['ETL','Data Warehouse','Power BI','Tableau','Excel','Business Intelligence']]
  ],
  'stom': [
    ['Core skills', ['ServiceNow','SLA','SOP','Process Improvement','Stakeholder Management','Documentation','Communication Skills','MS Office','Excel']]
  ],
  'power-bi': [
    ['Core skills', ['Power BI','Power Query','SQL','Data Analysis','Business Intelligence']],
    ['Reporting tooling', ['Excel','Advanced Excel','MIS Reporting','Tableau','ETL']]
  ],
  'data-analyst': [
    ['Core skills', ['Data Analysis','SQL','Python','Business Intelligence']],
    ['Spreadsheet & BI tooling', ['Excel','Advanced Excel','VBA','Macros','Power BI','Power Query','Tableau','MIS Reporting']]
  ],
  'workday': [
    ['Core skills', ['Workday','Data Analysis','Stakeholder Management','Documentation','Communication Skills','Excel','MS Office']]
  ],
  'python-fullstack': [
    ['Core skills', ['Python','JavaScript','React','HTML','CSS','SQL','API Testing','ETL']]
  ],
  'java-fullstack': [
    ['Core skills', ['Java','Spring Boot','JavaScript','React','Angular','HTML','CSS','SQL','API Testing']]
  ],
  'qa-testing': [
    ['Core skills', ['Manual Testing','Automation Testing','Selenium','API Testing','Testing','SQL','Documentation','SOP','Quality Assurance','Quality Control']]
  ],
  'ib-operations': [
    ['Core skills', ['Investment Banking Operations','Settlements','Trade Settlement','Corporate Actions','Reconciliation','Custody','Fund Accounting']],
    ['Markets & payments', ['SWIFT','Derivatives','Equities','Fixed Income','FX','Treasury','Payments','Back Office','Middle Office','KYC','Excel']]
  ],
  'sap-fico': [
    ['Core skills', ['SAP','SAP FICO','Reconciliation','Internal Audit','Audit','Data Analysis','Fund Accounting','Excel','Advanced Excel','MS Office']]
  ],
  'web-dev': [
    ['Core skills', ['HTML','CSS','JavaScript','React','Angular','Python','SQL']]
  ],
  'dotnet': [
    ['Core skills', ['SQL','JavaScript','HTML','CSS','API Testing','Testing','Documentation']]
  ],
  'dbi': [
    ['Core skills', ['SQL','ETL','Data Warehouse','Business Intelligence','Data Analysis']],
    ['BI tooling', ['Power BI','Power Query','Tableau','MIS Reporting','Excel','Advanced Excel']]
  ]
};
