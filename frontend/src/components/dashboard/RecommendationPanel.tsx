import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  ChevronDown,
  ChevronUp,
  Clock,
  PlayCircle,
  ShieldAlert,
  Sparkles,
  Zap,
  BookOpen,
  X,
  Scale,
  ShieldCheck,
  HelpCircle,
  Activity,
  Layers,
  AlertOctagon,
} from 'lucide-react';
import {
  useConflicts,
  useRecommendations,
  useApplyRecommendation,
  useDecisionExplanation,
  useSidingStatus,
  useRunStressTest,
} from '../../hooks/useRailData';
import { CandidateActionItem, ConflictItem, StressTestResultData } from '../../types/api';
import './RecommendationPanel.css';

export const RecommendationPanel: React.FC = () => {
  const [profile, setProfile] = useState<string>('BALANCED');
  const [showAllCandidates, setShowAllCandidates] = useState<boolean>(false);
  const [showXAIModal, setShowXAIModal] = useState<boolean>(false);
  const [showStressModal, setShowStressModal] = useState<boolean>(false);
  const [stressDelayInjection, setStressDelayInjection] = useState<number>(0);
  const [stressResult, setStressResult] = useState<StressTestResultData | null>(null);
  const [appliedNotification, setAppliedNotification] = useState<string | null>(null);

  const { data: conflictsData } = useConflicts();
  const { data: recsData } = useRecommendations(profile);
  const { data: sidingData } = useSidingStatus();
  const applyMutation = useApplyRecommendation();
  const stressTestMutation = useRunStressTest();

  const conflicts = conflictsData?.conflicts || [];
  const candidates = recsData?.candidates || [];
  const recommended = recsData?.recommended;

  const { data: xaiData, isLoading: xaiLoading } = useDecisionExplanation(
    showXAIModal && recommended ? recommended.recommendation_id : null
  );

  const handleApply = (actionId: string, actionDesc: string) => {
    applyMutation.mutate(actionId, {
      onSuccess: () => {
        setAppliedNotification(`Action applied: ${actionDesc}`);
        setTimeout(() => setAppliedNotification(null), 4500);
      },
      onError: (err: any) => {
        setAppliedNotification(`Error: ${err.message}`);
        setTimeout(() => setAppliedNotification(null), 4500);
      },
    });
  };

  const getActionBadgeClass = (type: string) => {
    switch (type) {
      case 'PRIORITIZE_TRAIN':
        return 'badge-prioritize';
      case 'HOLD_TRAIN':
        return 'badge-hold';
      case 'CROSSING_WAIT':
        return 'badge-crossing';
      case 'SPEED_ADVISORY':
        return 'badge-speed';
      default:
        return 'badge-default';
    }
  };

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'severity-critical';
      case 'HIGH':
        return 'severity-high';
      default:
        return 'severity-medium';
    }
  };

  return (
    <div className="recommendation-panel-card">
      {/* ── Header & Profile Selector ── */}
      <div className="rec-header">
        <div className="rec-title-group">
          <span className="rec-title">
            <Cpu size={16} className="icon-ai" /> AI Dispatch Recommender
          </span>
          <span className="rec-badge-online">
            <Sparkles size={12} /> RAIL-15 XAI Active
          </span>
        </div>

        <div className="profile-selector-group">
          <label htmlFor="objective-profile">Objective:</label>
          <select
            id="objective-profile"
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            className="profile-select"
          >
            <option value="BALANCED">Balanced (Standard)</option>
            <option value="PRIORITY_FIRST">Priority First (Rajdhani/VB)</option>
            <option value="THROUGHPUT_MAX">Throughput Max</option>
            <option value="DELAY_MIN">Delay Minimization</option>
          </select>

          <button
            className="btn-stress-trigger"
            onClick={() => setShowStressModal(true)}
            title="Run 10-Train Saturation Stress Test (RAIL-16)"
          >
            <Activity size={13} /> Stress Test
          </button>
        </div>
      </div>

      {/* ── RAIL-16 Siding Capacity Status Strip ── */}
      {sidingData && (
        <div className="siding-status-strip">
          <div className="siding-summary-left">
            <Layers size={13} className="siding-icon" />
            <span className="siding-title">Loop Headroom:</span>
            <span className="siding-tag">KUR: {sidingData.sidings?.KUR?.available_headroom ?? 6}/6</span>
            <span className="siding-tag">BBS: {sidingData.sidings?.BBS?.available_headroom ?? 6}/6</span>
            <span className="siding-tag">PURI: {sidingData.sidings?.PURI?.available_headroom ?? 8}/8</span>
            <span className="siding-tag">SIL: {sidingData.sidings?.SIL?.available_headroom ?? 2}/2</span>
          </div>
          <div className="siding-summary-right">
            {sidingData.saturated_stations && sidingData.saturated_stations.length > 0 ? (
              <span className="siding-badge-saturated">
                <AlertOctagon size={11} /> Saturated: {sidingData.saturated_stations.join(', ')}
              </span>
            ) : (
              <span className="siding-badge-ok">
                <CheckCircle2 size={11} /> All Sidings Safe
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Notification Banner ── */}
      {appliedNotification && (
        <div className="applied-banner animate-fade-in">
          <CheckCircle2 size={15} />
          <span>{appliedNotification}</span>
        </div>
      )}

      {/* ── Active Conflicts Strip ── */}
      <div className="conflicts-strip">
        <div className="strip-title">
          <AlertTriangle size={14} /> Active Network Contention ({conflicts.length})
        </div>
        {conflicts.length > 0 ? (
          <div className="conflicts-list">
            {conflicts.map((c: ConflictItem) => (
              <div key={c.conflict_id} className="conflict-badge-item">
                <span className={`severity-tag ${getSeverityBadgeClass(c.severity)}`}>
                  {c.severity}
                </span>
                <span className="conflict-type-label">{c.conflict_type.replace('_', ' ')}</span>
                <span className="conflict-location">@{c.location}</span>
                <span className="conflict-trains">({c.train_ids.join(' vs ')})</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-conflicts-notice">
            <CheckCircle2 size={13} /> Corridor clear. No track contention detected.
          </div>
        )}
      </div>

      {/* ── Recommended Decision Card (Top Pick) ── */}
      {recommended ? (
        <div className="recommended-card">
          <div className="card-top-row">
            <div className="tag-recommended">
              <Zap size={13} /> Recommended AI Intervention
            </div>
            <div className="utility-score-badge">
              <span className="score-val">{recommended.score.toFixed(1)}</span>
              <span className="score-max">/100</span>
            </div>
          </div>

          <div className="action-type-row">
            <span className={`action-type-badge ${getActionBadgeClass(recommended.action_type)}`}>
              {recommended.action_type.replace('_', ' ')}
            </span>
            <span className="target-train">
              {recommended.target_train_name} ({recommended.target_train_id}) • P{recommended.target_train_priority}
            </span>
            <span className="action-location">@{recommended.target_location}</span>
          </div>

          <p className="trade-off-text">{recommended.trade_off_explanation}</p>

          <div className="impact-chips">
            <span className="chip delay">
              <Clock size={12} /> Delay: {recommended.expected_delay_change >= 0 ? `+${recommended.expected_delay_change.toFixed(1)}m` : `${recommended.expected_delay_change.toFixed(1)}m`}
            </span>
            {recommended.expected_waiting_change > 0 && (
              <span className="chip wait">
                <Clock size={12} /> Wait: +{recommended.expected_waiting_change.toFixed(1)}m
              </span>
            )}
            <span className="chip feasible">
              <CheckCircle2 size={12} /> Feasible
            </span>
          </div>

          <div className="sub-scores-meter">
            <div className="meter-label">
              <span>Objective Sub-Scores:</span>
              <span className="weights-note">
                Prio: {recommended.sub_scores.priority} | Delay: {recommended.sub_scores.delay} | Throughput: {recommended.sub_scores.throughput}
              </span>
            </div>
            <div className="score-progress-bar">
              <div
                className="score-fill"
                style={{ width: `${Math.min(100, Math.max(10, recommended.score))}%` }}
              />
            </div>
          </div>

          <div className="rec-action-buttons">
            <button
              onClick={() => handleApply(recommended.recommendation_id, recommended.action_type)}
              disabled={applyMutation.isPending}
              className="btn-apply-rec"
            >
              {applyMutation.isPending ? (
                <span>Applying Intervention...</span>
              ) : (
                <>
                  <PlayCircle size={15} /> Apply Intervention
                </>
              )}
            </button>

            <button
              onClick={() => setShowXAIModal(true)}
              className="btn-explain-xai"
              title="View Explainable AI decision rationale and regulatory audit"
            >
              <BookOpen size={14} />
              <span>Explain (XAI)</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="empty-recommendations">
          {conflicts.length > 0 ? (
            <span>Analyzing candidate actions...</span>
          ) : (
            <span>Load a scenario with active trains to generate AI dispatch decisions.</span>
          )}
        </div>
      )}

      {/* ── Expandable All Candidate Alternatives ── */}
      {candidates.length > 1 && (
        <div className="alternatives-section">
          <button
            onClick={() => setShowAllCandidates(!showAllCandidates)}
            className="btn-toggle-alternatives"
          >
            <span>All Evaluated Alternatives ({candidates.length})</span>
            {showAllCandidates ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>

          {showAllCandidates && (
            <div className="candidates-list animate-slide-down">
              {candidates.map((c: CandidateActionItem, idx: number) => (
                <div key={c.recommendation_id} className={`candidate-item ${!c.feasible ? 'infeasible' : ''}`}>
                  <div className="cand-row-1">
                    <span className="cand-rank">#{idx + 1}</span>
                    <span className={`cand-badge ${getActionBadgeClass(c.action_type)}`}>
                      {c.action_type.replace('_', ' ')}
                    </span>
                    <span className="cand-train">{c.target_train_name}</span>
                    <span className="cand-score">{c.score.toFixed(1)}/100</span>
                  </div>

                  <div className="cand-desc">{c.description}</div>

                  {!c.feasible && (
                    <div className="cand-infeasible-reason">
                      <ShieldAlert size={12} /> {c.feasibility_reason}
                    </div>
                  )}

                  {c.feasible && c.recommendation_id !== recommended?.recommendation_id && (
                    <button
                      onClick={() => handleApply(c.recommendation_id, c.action_type)}
                      disabled={applyMutation.isPending}
                      className="btn-apply-alt"
                    >
                      Apply Alternative
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── RAIL-15: Explainable AI (XAI) Modal / Drawer ── */}
      {showXAIModal && (
        <div className="xai-modal-backdrop" onClick={() => setShowXAIModal(false)}>
          <div className="xai-modal-content animate-slide-down" onClick={(e) => e.stopPropagation()}>
            <div className="xai-modal-header">
              <div className="xai-title-group">
                <BookOpen size={18} className="icon-xai" />
                <div>
                  <h3 className="xai-heading">XAI Dispatch Decision Audit</h3>
                  <span className="xai-subheading">
                    Action ID: {recommended?.recommendation_id} • Score: {recommended?.score.toFixed(1)}/100
                  </span>
                </div>
              </div>
              <button className="btn-close-xai" onClick={() => setShowXAIModal(false)}>
                <X size={16} />
              </button>
            </div>

            <div className="xai-modal-body">
              {xaiLoading ? (
                <div className="xai-loading">Generating Explainable AI decision audit...</div>
              ) : xaiData ? (
                <div className="xai-sections">
                  {/* 1. Executive Summary */}
                  <div className="xai-card exec-card">
                    <h4 className="xai-card-title">
                      <Zap size={14} /> Executive Summary
                    </h4>
                    <p className="xai-exec-text">{xaiData.executive_summary}</p>
                  </div>

                  {/* 2. Key Decision Drivers */}
                  <div className="xai-card">
                    <h4 className="xai-card-title">
                      <Scale size={14} /> Key Factor Attributions & Model Drivers
                    </h4>
                    <div className="xai-drivers-list">
                      {xaiData.key_drivers.map((d, i) => (
                        <div key={i} className="xai-driver-item">
                          <div className="driver-top">
                            <span className="driver-name">{d.factor_name}</span>
                            <span className="driver-pct">{d.impact_pct}% weight</span>
                          </div>
                          <div className="driver-bar">
                            <div className="driver-bar-fill" style={{ width: `${d.impact_pct * 2}%` }} />
                          </div>
                          <p className="driver-desc">{d.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 3. Counterfactual Cases */}
                  <div className="xai-card">
                    <h4 className="xai-card-title">
                      <HelpCircle size={14} /> Counterfactual Reasoning (Rejected Alternatives)
                    </h4>
                    <div className="xai-counterfactual-list">
                      {xaiData.counterfactuals.map((cf, i) => (
                        <div key={i} className="xai-cf-item">
                          <div className="cf-action">❌ Alternative: {cf.alternative_action}</div>
                          <div className="cf-consequence">Impact: {cf.projected_consequence}</div>
                          <div className="cf-reason">Why Rejected: {cf.why_rejected}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 4. Regulatory & Safety Rules */}
                  <div className="xai-card">
                    <h4 className="xai-card-title">
                      <ShieldCheck size={14} /> Indian Railways Regulatory & Safety Compliance
                    </h4>
                    <div className="xai-reg-list">
                      {xaiData.regulatory_compliance.map((r, i) => (
                        <div key={i} className="xai-reg-item">
                          <div className="reg-top">
                            <span className="reg-code">{r.rule_code}: {r.rule_name}</span>
                            <span className="reg-badge">{r.compliance_status}</span>
                          </div>
                          <div className="reg-auth">{r.authority}</div>
                          <p className="reg-exp">{r.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="xai-error">Unable to load decision explanation.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── RAIL-16 Stress Test Modal ── */}
      {showStressModal && (
        <div className="xai-modal-overlay" onClick={() => setShowStressModal(false)}>
          <div className="xai-modal-content stress-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="xai-modal-header">
              <div className="xai-modal-title-group">
                <Activity size={20} className="icon-ai" />
                <div>
                  <h3 className="xai-modal-title">Edge-Case Stress Testing & Siding Resilience</h3>
                  <div className="xai-modal-subtitle">
                    10-train corridor saturation under extreme delay injection & Temporary Speed Restrictions (TSRs)
                  </div>
                </div>
              </div>
              <button className="xai-modal-close" onClick={() => setShowStressModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="stress-modal-body">
              {/* Injection Controls */}
              <div className="stress-control-bar">
                <div className="stress-field">
                  <label>Additional Delay Injection:</label>
                  <select
                    value={stressDelayInjection}
                    onChange={(e) => setStressDelayInjection(Number(e.target.value))}
                    className="profile-select"
                  >
                    <option value={0}>+0 min (Scenario Defaults: +15m to +50m)</option>
                    <option value={15}>+15 min Additional (High Gridlock)</option>
                    <option value={30}>+30 min Additional (Extreme Cascade)</option>
                    <option value={45}>+45 min Additional (Critical Monsoon Flooding)</option>
                  </select>
                </div>

                <button
                  className="btn-run-stress"
                  disabled={stressTestMutation.isPending}
                  onClick={() => {
                    stressTestMutation.mutate(
                      {
                        scenario_id: 'scenario_003',
                        additional_delay_minutes: stressDelayInjection,
                        enforce_siding_limits: true,
                      },
                      {
                        onSuccess: (data) => setStressResult(data),
                      }
                    );
                  }}
                >
                  <PlayCircle size={15} />
                  {stressTestMutation.isPending ? 'Simulating 10 Trains...' : 'Run 10-Train Saturation Test'}
                </button>
              </div>

              {/* Stress Results View */}
              {stressResult && (
                <div className="stress-results-container animate-fade-in">
                  <div className="stress-kpi-grid">
                    <div className="stress-kpi-card highlight-kpi">
                      <div className="stress-kpi-val">{stressResult.deadlocks_prevented}</div>
                      <div className="stress-kpi-lbl">Secondary Deadlocks Prevented</div>
                      <div className="stress-kpi-sub">KUR throat & SIL single line</div>
                    </div>

                    <div className="stress-kpi-card">
                      <div className="stress-kpi-val">{stressResult.resilience_score}/100</div>
                      <div className="stress-kpi-lbl">System Resilience Score</div>
                      <div className="stress-kpi-sub">Stability index under load</div>
                    </div>

                    <div className="stress-kpi-card">
                      <div className="stress-kpi-val">-{stressResult.delay_saved_pct}%</div>
                      <div className="stress-kpi-lbl">Delay Saved vs Baseline</div>
                      <div className="stress-kpi-sub">{stressResult.baseline_delay}m → {stressResult.ai_optimized_delay}m</div>
                    </div>

                    <div className="stress-kpi-card">
                      <div className="stress-kpi-val text-green">100% Safe</div>
                      <div className="stress-kpi-lbl">P1 Train Protection</div>
                      <div className="stress-kpi-sub">Rajdhani & Vande Bharat</div>
                    </div>

                    <div className="stress-kpi-card">
                      <div className="stress-kpi-val">{stressResult.recovery_time_ms.toFixed(1)} ms</div>
                      <div className="stress-kpi-lbl">Solver Recovery Time</div>
                      <div className="stress-kpi-sub">10-train multi-conflict graph</div>
                    </div>
                  </div>

                  {/* Siding Peak Utilization */}
                  <div className="xai-card" style={{ marginTop: '1rem' }}>
                    <h4 className="xai-card-title">
                      <Layers size={14} /> Peak Station Loop / Siding Capacity Utilization Under Saturation
                    </h4>
                    <div className="siding-peak-bars">
                      {Object.entries(stressResult.station_siding_peaks).map(([st, pct]) => (
                        <div key={st} className="siding-bar-row">
                          <div className="siding-bar-labels">
                            <span className="siding-st-code">{st}</span>
                            <span className="siding-st-pct">{pct}% peak</span>
                          </div>
                          <div className="siding-progress-track">
                            <div
                              className={`siding-progress-fill ${
                                pct >= 100 ? 'fill-crit' : pct >= 75 ? 'fill-warn' : 'fill-ok'
                              }`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
