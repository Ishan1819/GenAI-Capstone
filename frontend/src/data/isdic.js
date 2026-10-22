// Content sourced from the public pages of https://isdic.in (scraped for this project).

export const SITE = "https://isdic.in";

export const STATS = [
  { value: "4", label: "Domain communities" },
  { value: "28", label: "Activity formats in the plan" },
  { value: "3", label: "Skill levels per domain" },
  { value: "40", label: "Tools in the training stack" },
];

export const DOMAINS = [
  {
    id: "cyber",
    name: "Cybersecurity",
    community: "Cybersecurity Community",
    color: "#a4443a",
    tagline:
      "Hands-on attack and defence practice, not textbook theory. Every session ends with a student having done something real: solved a flag, exploited a vulnerability, or secured a system.",
    highlights: ["Ethical Hacking", "CTF Competitions", "Threat Labs", "Security Fundamentals"],
    levels: [
      { name: "Foundation", months: "Months 1–3", items: ["Linux command line basics", "Networking fundamentals", "Intro to Kali Linux", "First TryHackMe room"] },
      { name: "Intermediate", months: "Months 4–8", items: ["OWASP Top 10 in practice", "Burp Suite proficiency", "Nmap and recon tools", "HackTheBox easy machines"] },
      { name: "Advanced", months: "Months 9–12", items: ["Active Directory attacks", "Malware analysis basics", "Bug bounty hunting", "CTF leadership & design"] },
    ],
    tools: ["TryHackMe", "HackTheBox", "PicoCTF", "Kali Linux", "Burp Suite", "Wireshark", "Nmap", "Metasploit", "OWASP WebGoat", "VulnHub"],
    flagship: {
      name: "Capture The Flag (CTF) Competition",
      text: "Timed team challenge where students exploit intentionally vulnerable systems to capture hidden flags. Three parallel tracks (Beginner, Intermediate, Advanced) so no one is excluded.",
      tags: ["Web exploitation", "Reverse engineering", "Cryptography", "Forensics", "OSINT"],
    },
    outcomes: [
      { title: "At least 1 certification", text: "Every active member targets eJPT or CompTIA Security+ before the academic year ends." },
      { title: "Public CTF ranking", text: "A verified HackTheBox or TryHackMe profile showing measurable progress." },
      { title: "Interview-ready portfolio", text: "GitHub with 2+ security writeups, vulnerability research or lab documentation." },
    ],
    questions: ["What does the Cybersecurity foundation level cover?", "Which certifications does the cyber community prepare for?", "How does the CTF competition work?"],
  },
  {
    id: "aiml",
    name: "AI and ML",
    community: "AI, ML & Data Science",
    color: "#7a5a86",
    tagline:
      "Move from “I've used ChatGPT” to “I built and deployed a model.” Every session runs real code in Google Colab, building a portfolio recruiters can see and test.",
    highlights: ["ML Bootcamps", "LLM & Gen AI", "Data Analytics", "AI Projects"],
    levels: [
      { name: "Foundation", months: "Months 1–3", items: ["Python for data science", "NumPy and Pandas", "Data visualization basics", "First Kaggle submission"] },
      { name: "ML practitioner", months: "Months 4–8", items: ["Supervised and unsupervised ML", "Model evaluation and tuning", "Neural networks intro", "Deployed Streamlit app"] },
      { name: "Advanced", months: "Months 9–12", items: ["Deep learning with PyTorch", "LLM fine-tuning and RAG", "MLOps fundamentals", "Kaggle top 30% ranking"] },
    ],
    tools: ["Google Colab", "Kaggle Notebooks", "Hugging Face", "Scikit-learn", "PyTorch", "LangChain", "Streamlit", "Gradio", "Weights & Biases", "FastAI"],
    flagship: {
      name: "Weekend ML Bootcamp",
      text: "From zero to deployed model in 2 days: Python and data cleaning on day 1, Scikit-learn training and Streamlit deployment on Hugging Face Spaces on day 2. Students leave with a live app.",
      tags: ["Sentiment analyzer", "Price predictor", "Image classifier", "Custom chatbot"],
    },
    outcomes: [
      { title: "Live deployed model", text: "A Streamlit or Gradio app on Hugging Face Spaces with a public URL." },
      { title: "Kaggle public profile", text: "Verified competition participation with notebooks showing real ML methodology." },
      { title: "Project portfolio", text: "GitHub with 2+ end-to-end ML projects across different techniques." },
    ],
    questions: ["What will I learn in the AI & ML foundation level?", "What is the Weekend ML Bootcamp?", "Does the AI track cover LLMs and RAG?"],
  },
  {
    id: "cloud",
    name: "Cloud and DevOps",
    community: "Cloud & DevOps Community",
    color: "#3b6680",
    tagline:
      "Cloud fundamentals through to CI/CD pipelines, preparing students for the infrastructure that actually runs modern software teams. Students deploy, not watch.",
    highlights: ["Cloud Fundamentals", "CI/CD Pipelines", "Deployment Labs", "Infrastructure as Code"],
    levels: [
      { name: "Cloud basics", months: "Months 1–3", items: ["Linux for cloud admins", "First AWS Free Tier deploy", "S3 static site hosting", "EC2 management basics"] },
      { name: "DevOps practitioner", months: "Months 4–8", items: ["Docker containers", "GitHub Actions CI/CD", "AWS Solutions Architect prep", "Terraform basics"] },
      { name: "Cloud engineer", months: "Months 9–12", items: ["Kubernetes in production", "Multi-cloud architecture", "SRE practices", "Cost optimization strategies"] },
    ],
    tools: ["AWS Free Tier", "GCP Free Credits", "Azure for Students", "GitHub Actions", "Docker Desktop", "Minikube", "Terraform", "Prometheus", "Grafana OSS", "Play with K8s"],
    flagship: {
      name: "Multi-team Cloud Infrastructure Hackathon",
      text: "A 24-hour event where teams build and deploy a complete cloud-native application (frontend, backend, database, CI/CD and monitoring) on real cloud, judged on uptime, architecture and cost.",
      tags: ["Architecture quality", "Uptime", "CI/CD", "Cost optimization", "Security posture"],
    },
    outcomes: [
      { title: "Cloud certification", text: "At least one AWS, GCP or Azure certification before the year ends." },
      { title: "Live cloud project", text: "A full-stack app on cloud with CI/CD, monitoring and a public URL." },
      { title: "Infrastructure portfolio", text: "GitHub with Terraform configs, Dockerfiles and architecture diagrams." },
    ],
    questions: ["What does the Cloud & DevOps track cover?", "When is the Kubernetes workshop in the year?", "Which cloud certifications are targeted?"],
  },
  {
    id: "dev",
    name: "Software Development",
    community: "Developer Community",
    color: "#4f7a45",
    tagline:
      "Hackathons, open-source contribution and full-stack bootcamps. Where coders become builders, and builders become engineers others want to hire.",
    highlights: ["Hackathons", "Open Source", "System Design", "Full-Stack"],
    levels: [
      { name: "Coder", months: "Months 1–3", items: ["Git and GitHub fluency", "DSA basics (arrays, trees)", "First open source PR", "Personal project deployed"] },
      { name: "Builder", months: "Months 4–8", items: ["Full-stack app with database", "50+ LeetCode problems", "Hackathon participation", "System design basics"] },
      { name: "Engineer", months: "Months 9–12", items: ["Production app with live users", "3+ merged OSS pull requests", "System design interview-ready", "Mentoring juniors"] },
    ],
    tools: ["GitHub", "LeetCode", "Render", "Railway", "Vercel", "VS Code", "Replit", "Postman", "Figma", "Notion"],
    flagship: {
      name: "48-Hour Hackathon",
      text: "Teams of 4 build a working product in 48 hours around a real problem statement, judged by industry mentors. Top 3 teams win sponsor prizes and fast-track to internship interviews.",
      tags: ["Product thinking", "Code quality", "UI and UX", "Pitch clarity"],
    },
    outcomes: [
      { title: "Live product", text: "A full-stack application with real users, a public URL and clean code." },
      { title: "Open source contributor", text: "At least 3 merged pull requests in real external repositories." },
      { title: "Interview-ready", text: "100+ LeetCode problems, 2 system design patterns practised, a mock interview done." },
    ],
    questions: ["What happens in the 48-hour hackathon?", "How do I get started with open source in the developer community?", "What does the Builder level include?"],
  },
];

export const MODEL_STEPS = [
  { title: "The college partners with ISDIC", text: "At zero cost. The college provides the space; ISDIC brings the curriculum, the mentors and the community structure." },
  { title: "A skill development centre launches", text: "The centre goes live with four domain tracks. Students organise into communities, run their own events and build real projects." },
  { title: "Members build a portfolio", text: "A structured year of curriculum, competitions, hackathons, open source and industry certifications." },
];

export const QUARTERS = [
  { name: "Quarter 1", months: "Jan – Mar", items: [["Cyber", "Beginner CTF"], ["AI & ML", "ML bootcamp (2 days)"], ["Cloud", "First AWS deploy lab"], ["Dev", "Git + OSS onboarding"]] },
  { name: "Quarter 2", months: "Apr – Jun", items: [["Cyber", "Inter-college CTF"], ["AI & ML", "Kaggle competition sprint"], ["Cloud", "CI/CD build challenge"], ["Dev", "Hackathon 1 (48 hrs)"]] },
  { name: "Quarter 3", months: "Jul – Sep", items: [["Cyber", "Red vs. blue simulation"], ["AI & ML", "Deep learning bootcamp"], ["Cloud", "Kubernetes 2-day workshop"], ["Dev", "Open source sprint 2"]] },
  { name: "Quarter 4", months: "Oct – Dec", items: [["Cyber", "Annual security summit"], ["AI & ML", "AI for social good demo"], ["Cloud", "Cloud infra hackathon (24h)"], ["Dev", "Hackathon 2 (flagship)"]] },
];

export const WHY = [
  { title: "Free for students and colleges", text: "The skill gap is a national problem; access should not be a privilege." },
  { title: "A structured year, not ad-hoc events", text: "Every domain has a published quarter-by-quarter plan, three levels, a flagship event and defined outcomes." },
  { title: "Focused on tier-2 and tier-3 cities", text: "ISDIC goes where the talent is, not only where the technology hubs are." },
  { title: "Guided by working practitioners", text: "The curriculum is shaped by people currently building and defending real systems." },
];

export const CHAPTERS = {
  active: { city: "Pune", state: "Maharashtra", lead: "Chetan Wani", text: "A local hub for students, professionals and technology enthusiasts, with regular meetups, technical sessions, workshops and mentorship across all four domains." },
  planned: [["Bangalore", "Karnataka"], ["Hyderabad", "Telangana"], ["Chennai", "Tamil Nadu"], ["Mumbai", "Maharashtra"], ["Nashik", "Maharashtra"]],
};

export const LEADERS = [
  { name: "Chetan Kawley", role: "Founder and CEO, Threatactix", area: "Threat hunting & incident response" },
  { name: "Nilesh Miskin", role: "Chief Digital Officer, Vikasietum", area: "Full-stack, cloud & microservices" },
  { name: "Kedar Badve", role: "Founder & Director, CyberArt Solutions", area: "Cyber forensics, VA/PT & compliance" },
  { name: "Mandar Amrite", role: "Consultant & Entrepreneur", area: "Enterprise security architecture" },
];
