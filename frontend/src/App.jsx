import { useRoute } from "./router.js";
import Navbar from "./components/layout/Navbar.jsx";
import Footer from "./components/layout/Footer.jsx";
import ChatWidget from "./components/layout/ChatWidget.jsx";
import PageHeader from "./components/layout/PageHeader.jsx";
import Home from "./pages/Home.jsx";
import Domain from "./pages/Domain.jsx";
import Chat from "./components/Chat.jsx";
import Search from "./components/Search.jsx";
import LearningPath from "./components/LearningPath.jsx";
import ResumeCheck from "./components/ResumeCheck.jsx";
import Recommend from "./components/Recommend.jsx";
import Quiz from "./components/Quiz.jsx";
import Projects from "./components/Projects.jsx";
import AdminApp from "./admin/AdminApp.jsx";

function Tool({ eyebrow, title, intro, children }) {
  return (
    <>
      <PageHeader eyebrow={eyebrow} title={title}>{intro}</PageHeader>
      <div className="container section tool-page">{children}</div>
    </>
  );
}

function Page({ path, params }) {
  if (path.startsWith("/domains/")) return <Domain id={path.split("/")[2]} />;
  switch (path) {
    case "/assistant":
      return (
        <Tool eyebrow="AI assistant" title="Ask ISDIC" intro="Answers come only from ISDIC's own content, with sources. If it doesn't know, it says so and forwards the question to the team.">
          <Chat key={params.get("q") || ""} initialQuestion={params.get("q") || ""} />
        </Tool>
      );
    case "/search":
      return (
        <Tool eyebrow="Module 2" title="Community search" intro="Search members, events and pages in plain language. Filters are picked up from what you type, or set them yourself.">
          <Search />
        </Tool>
      );
    case "/path":
      return (
        <Tool eyebrow="Learning path" title="Build your roadmap" intro="Tell us your goal and what you already know. The roadmap follows the curriculum's prerequisites and skips what you've covered.">
          <LearningPath initialDomain={params.get("domain") || ""} />
        </Tool>
      );
    case "/resume":
      return (
        <Tool eyebrow="Resume check" title="Where do you fit?" intro="Upload a PDF or text resume to see your best-fit domain and level, and the skills to build next. It is analysed in memory and not stored.">
          <ResumeCheck />
        </Tool>
      );
    case "/for-you":
      return (
        <Tool eyebrow="Module 3" title="Recommended for you" intro="People, events and curriculum suggested from your profile, each with the reason it was picked. Demo mode uses fictional members.">
          <Recommend />
        </Tool>
      );
    case "/quiz":
      return (
        <Tool eyebrow="Skill quiz" title="How ready are you?" intro="Five questions written from the curriculum of your domain and level. See what you know, and what to review before the next level.">
          <Quiz initialDomain={params.get("domain") || ""} />
        </Tool>
      );
    case "/projects":
      return (
        <Tool eyebrow="Project ideas" title="Build something worth showing" intro="ISDIC's tracks end in a public portfolio. Get project ideas that use your track's tools, fit your level and match what you care about.">
          <Projects initialDomain={params.get("domain") || ""} />
        </Tool>
      );
    default:
      return <Home />;
  }
}

export default function App() {
  const { path, params } = useRoute();
  // Admin console is a separate app: not linked from the member portal, behind a token
  if (path === "/admin" || path.startsWith("/admin/")) return <AdminApp path={path} />;
  return (
    <div className="app">
      <Navbar path={path} />
      <main><Page path={path} params={params} /></main>
      <Footer />
      {path !== "/assistant" && <ChatWidget />}
    </div>
  );
}
