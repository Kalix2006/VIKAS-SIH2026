import { useState } from "react";
import { useAuth } from "../../lib/auth";
import { CourseList } from "./CourseList";
import { AlternativesView } from "./AlternativesView";
import { ProficiencyExpectationsView } from "./ProficiencyExpectations";
import { TraineeChat } from "./TraineeChat";
import { AlertsView } from "./AlertsView";
import {
  GraduationCap,
  Sparkles,
  Bot,
  Bell,
  LogOut,
  MapPin,
  Compass,
} from "lucide-react";

type TraineeTab = "courses" | "alternatives" | "skills" | "chat" | "alerts";

export function TraineeLayout() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<TraineeTab>("courses");
  const [selectedCourseForAlternatives, setSelectedCourseForAlternatives] =
    useState<string | null>(null);

  const handleSelectCourseAlternatives = (courseId: string) => {
    setSelectedCourseForAlternatives(courseId);
    setActiveTab("alternatives");
  };

  const navItems = [
    {
      id: "courses" as const,
      label: "Courses",
      icon: GraduationCap,
      description: "District catalog & demand",
    },
    {
      id: "skills" as const,
      label: "Skills in Demand",
      icon: Sparkles,
      description: "Employer requirements",
    },
    {
      id: "chat" as const,
      label: "AI Counselor",
      icon: Bot,
      description: "Grounded career advisor",
    },
    {
      id: "alerts" as const,
      label: "Notices",
      icon: Bell,
      description: "Curriculum updates",
    },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 pb-20 sm:pb-0">
      {/* Top Header */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Logo & Platform Name */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-xs">
              <Compass className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-slate-900">
                  VIKAS
                </h1>
                <span className="rounded-md bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                  Trainee Portal
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium hidden sm:block">
                Viksit India Kaushal Alignment System
              </p>
            </div>
          </div>

          {/* User Info & Actions */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
              <MapPin className="h-3.5 w-3.5 text-emerald-600" />
              <span className="hidden sm:inline">District:</span>
              <span className="font-semibold text-slate-900">Pune</span>
            </div>

            <div className="hidden md:flex flex-col text-right text-xs">
              <span className="font-semibold text-slate-800">{user?.full_name || "Vocational Trainee"}</span>
              <span className="text-[11px] text-slate-400">{user?.email}</span>
            </div>

            <button
              onClick={logout}
              title="Sign Out"
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Desktop Tab Navigation */}
        <div className="hidden sm:block border-t border-slate-100 bg-white">
          <div className="mx-auto flex max-w-7xl gap-1 px-4 sm:px-6">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                activeTab === item.id ||
                (activeTab === "alternatives" && item.id === "courses");
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                  }}
                  className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition-colors ${
                    isActive
                      ? "border-emerald-600 text-emerald-700"
                      : "border-transparent text-slate-600 hover:border-slate-300 hover:text-slate-900"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Main Page Body */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
        {activeTab === "courses" && (
          <CourseList onSelectCourseAlternatives={handleSelectCourseAlternatives} />
        )}

        {activeTab === "alternatives" && (
          selectedCourseForAlternatives ? (
            <AlternativesView
              courseId={selectedCourseForAlternatives}
              onBack={() => setActiveTab("courses")}
            />
          ) : (
            <CourseList onSelectCourseAlternatives={handleSelectCourseAlternatives} />
          )
        )}

        {activeTab === "skills" && <ProficiencyExpectationsView />}

        {activeTab === "chat" && <TraineeChat />}

        {activeTab === "alerts" && <AlertsView />}
      </main>

      {/* Mobile Bottom Navigation Bar (usable on 375px viewports) */}
      <nav className="sm:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-slate-200 bg-white/95 backdrop-blur-md px-2 py-2">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              activeTab === item.id ||
              (activeTab === "alternatives" && item.id === "courses");
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                }}
                className={`flex flex-col items-center gap-1 px-3 py-1 text-[10px] font-medium transition-colors ${
                  isActive
                    ? "text-emerald-700 font-bold"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? "text-emerald-600" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

