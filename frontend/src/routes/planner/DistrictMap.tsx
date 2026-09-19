import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  MapPin,
  RefreshCw,
  Scale,
  ShieldAlert,
} from "lucide-react";
import { api } from "../../lib/api";
import { CapacityPlanExportModal } from "./CapacityPlanExportModal";

export interface DistrictMapSummary {
  id: string;
  name: string;
  state: string;
  centroid_lat: number;
  centroid_lng: number;
  active_trades_count: number;
  flagged_trades_count: number;
  total_job_volume: number;
  alignment_health_score: number;
  health_category: "Healthy" | "Moderate Drift" | "Critical Divergence";
  divergence_index: number;
}

export interface PlannerMapResponse {
  districts: DistrictMapSummary[];
  state_avg_health: number;
  total_districts: number;
  critical_districts_count: number;
  formula_definition: string;
}

export const DistrictMap: React.FC = () => {
  const [data, setData] = useState<PlannerMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDistrictForExport, setSelectedDistrictForExport] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const fetchMapData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api<PlannerMapResponse>("/planner/map");
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load state alignment map.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMapData();
  }, []);

  const getMarkerColors = (score: number) => {
    if (score >= 75.0) {
      return {
        color: "#059669",
        fillColor: "#10b981",
        label: "Healthy",
        badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-300",
      };
    }
    if (score >= 50.0) {
      return {
        color: "#d97706",
        fillColor: "#f59e0b",
        label: "Moderate Drift",
        badgeClass: "bg-amber-100 text-amber-800 border-amber-300",
      };
    }
    return {
      color: "#e11d48",
      fillColor: "#f43f5e",
      label: "Critical Divergence",
      badgeClass: "bg-rose-100 text-rose-800 border-rose-300",
    };
  };

  // Center on Maharashtra / Central India
  const defaultCenter: [number, number] = [19.2, 75.2];

  return (
    <div className="space-y-6">
      {/* Header & KPI Summary */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              State Skill Alignment Heatmap
            </h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700 border border-indigo-200">
              <Activity className="h-3.5 w-3.5" /> Empirical Health Index
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Geographic overview of district-level trade alignment, vacancy volumes, and curricular drift across vocational institutes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchMapData}
            title="Refresh Map Data"
            className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-colors shadow-2xs"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* KPI Cards & Formula Banner */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Monitored Districts
              </span>
              <MapPin className="h-4 w-4 text-indigo-600" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-black text-slate-900" data-testid="kpi-total-districts">
                {data.total_districts}
              </span>
              <span className="text-xs text-slate-400 font-medium">administrative units</span>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                State Avg Alignment Health
              </span>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-black text-slate-900" data-testid="kpi-state-avg-health">
                {data.state_avg_health}
              </span>
              <span className="text-xs text-slate-400 font-medium">/ 100 Index</span>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Critical Priority Districts
              </span>
              <ShieldAlert className="h-4 w-4 text-rose-600" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-black text-rose-600" data-testid="kpi-critical-districts">
                {data.critical_districts_count}
              </span>
              <span className="text-xs text-rose-700/80 font-medium">require immediate review</span>
            </div>
          </div>
        </div>
      )}

      {/* Formula Specification Banner */}
      <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-indigo-900 font-bold">
          <Scale className="h-4 w-4 text-indigo-600 shrink-0" />
          <span>Statutory Health Formula:</span>
          <code className="bg-white/80 px-2 py-1 rounded-lg border border-indigo-200/60 font-mono text-[11px] text-indigo-950 font-semibold">
            AHI = 100 - [∑(Gap_Score × ln(1 + Volume)) / ∑(ln(1 + Volume))]
          </code>
        </div>
        <span className="text-indigo-700/80 text-[11px]">
          Volume-weighted empirical formulation • Zero LLM scoring
        </span>
      </div>

      {loading && (
        <div className="flex min-h-[400px] flex-col items-center justify-center gap-3 bg-white rounded-3xl border border-slate-200">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Loading Leaflet OpenStreetMap canvas...</p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-rose-500" />
          <p className="mt-2 text-sm font-semibold text-rose-800">{error}</p>
          <button
            onClick={fetchMapData}
            className="mt-3 rounded-xl bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* Map Container & Legend */}
      {!loading && !error && data && (
        <div className="relative rounded-3xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          {/* Map canvas */}
          <div className="h-[520px] w-full" data-testid="leaflet-map-canvas">
            <MapContainer
              center={defaultCenter}
              zoom={7}
              scrollWheelZoom={false}
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {data.districts.map((district) => {
                const colors = getMarkerColors(district.alignment_health_score);

                return (
                  <CircleMarker
                    key={district.id}
                    center={[district.centroid_lat, district.centroid_lng]}
                    radius={16}
                    pathOptions={{
                      color: colors.color,
                      fillColor: colors.fillColor,
                      fillOpacity: 0.8,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div className="p-1 space-y-2 min-w-[200px] font-sans">
                        <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
                          <h4 className="font-bold text-sm text-slate-900">{district.name}</h4>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-bold border ${colors.badgeClass}`}
                          >
                            {district.alignment_health_score}/100
                          </span>
                        </div>

                        <div className="text-xs space-y-1 text-slate-600">
                          <div className="flex justify-between">
                            <span>Health Status:</span>
                            <strong className="text-slate-800">{colors.label}</strong>
                          </div>
                          <div className="flex justify-between">
                            <span>Active Trades:</span>
                            <span className="font-semibold text-slate-800">{district.active_trades_count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Flagged Trades:</span>
                            <span className="font-semibold text-rose-700">{district.flagged_trades_count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Job Postings:</span>
                            <span className="font-semibold text-slate-800">{district.total_job_volume}</span>
                          </div>
                        </div>

                        <div className="pt-2 flex flex-col gap-1.5 border-t border-slate-100">
                          <Link
                            to={`/planner/districts/${district.id}`}
                            className="flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-indigo-700 transition-colors shadow-2xs"
                          >
                            Drill Down Table <ArrowRight className="h-3 w-3" />
                          </Link>
                          <button
                            type="button"
                            onClick={() =>
                              setSelectedDistrictForExport({
                                id: district.id,
                                name: district.name,
                              })
                            }
                            className="flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
                          >
                            <FileSpreadsheet className="h-3 w-3 text-emerald-600" />
                            Capacity Plan
                          </button>
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </MapContainer>
          </div>

          {/* Floating Map Legend */}
          <div className="absolute bottom-4 right-4 z-[1000] rounded-2xl border border-slate-200 bg-white/95 p-3.5 backdrop-blur-md shadow-md text-xs space-y-2">
            <span className="font-bold text-slate-800 block text-[11px] uppercase tracking-wider">
              Health Index Legend
            </span>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-emerald-500 border border-emerald-600" />
              <span className="text-slate-600">Healthy (≥ 75)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-amber-500 border border-amber-600" />
              <span className="text-slate-600">Moderate Drift (50 - 74)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-rose-500 border border-rose-600" />
              <span className="text-slate-600">Critical Divergence (&lt; 50)</span>
            </div>
          </div>
        </div>
      )}

      {/* Capacity Export Modal */}
      {selectedDistrictForExport && (
        <CapacityPlanExportModal
          isOpen={!!selectedDistrictForExport}
          onClose={() => setSelectedDistrictForExport(null)}
          districtId={selectedDistrictForExport.id}
          districtName={selectedDistrictForExport.name}
        />
      )}
    </div>
  );
};
export default DistrictMap;
