import React, { useState, useEffect } from 'react';
import {
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  X,
  Sparkles,
  MonitorPlay,
  Cpu,
  Layers,
  BarChart3,
} from 'lucide-react';
import { useAppStore } from '../../stores/useAppStore';
import {
  useSimulationControlActions,
  useApplyRecommendation,
  useRecommendations,
} from '../../hooks/useRailData';
import './DemoController.css';

interface DemoStep {
  stepNumber: number;
  title: string;
  badge: string;
  narration: string;
  highlightIcon: React.ReactNode;
  action: () => void;
}

export const DemoController: React.FC = () => {
  const {
    isDemoMode,
    setIsDemoMode,
    setActiveTab,
    setActiveScenarioId,
  } = useAppStore();

  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isAutoplay, setIsAutoplay] = useState<boolean>(true);

  const { startSimulation, setSpeed, resetSimulation } = useSimulationControlActions();
  const applyMutation = useApplyRecommendation();
  const { data: recsData } = useRecommendations('BALANCED');

  const steps: DemoStep[] = [
    {
      stepNumber: 1,
      title: 'Digital Twin & Corridor Ingestion',
      badge: 'Step 1: Network Ingestion',
      narration:
        'East Coast Railway Khurda Division loaded: 11 station nodes, 10 block sections, and dual single-line branches (Puri & Brahmapur) initialised in real-time.',
      highlightIcon: <Layers size={18} className="text-blue" />,
      action: () => {
        setActiveTab('dashboard');
        setActiveScenarioId('scenario_001');
      },
    },
    {
      stepNumber: 2,
      title: 'Discrete-Event Train Simulation',
      badge: 'Step 2: Traffic Movement',
      narration:
        'Fast-forward simulation active at 5x: Priority 1 New Delhi Rajdhani (T003) and Priority 2 Puri Express (T001) approach Khurda Road Junction from opposing lines.',
      highlightIcon: <Play size={18} className="text-green" />,
      action: () => {
        setActiveTab('dashboard');
        startSimulation.mutate();
        setSpeed.mutate(5.0);
      },
    },
    {
      stepNumber: 3,
      title: 'Predictive ML Congestion & Conflict Contention',
      badge: 'Step 3: Bottleneck Alert',
      narration:
        'XGBoost ML Section Model detects single-line track saturation (Risk > 75%); Conflict Engine flags critical junction contention CONF_001 at Khurda Road (KUR).',
      highlightIcon: <Sparkles size={18} className="text-amber" />,
      action: () => {
        setActiveTab('dashboard');
      },
    },
    {
      stepNumber: 4,
      title: 'Autonomous AI Dispatch Optimization & XAI',
      badge: 'Step 4: AI Decision',
      narration:
        'Multi-Objective Engine synthesizes Pareto trade-off: Grants green corridor to P1 Rajdhani and regulates P2 Puri Express in loop siding under Indian Railways G&SR 4.23.',
      highlightIcon: <Cpu size={18} className="text-purple" />,
      action: () => {
        setActiveTab('dashboard');
        const firstActId = recsData?.recommended?.recommendation_id || 'CONF_001_ACT_PRIO_HIGH';
        applyMutation.mutate(firstActId);
      },
    },
    {
      stepNumber: 5,
      title: 'What-If Analytics & Capstone Defense Proof',
      badge: 'Step 5: Comparative Proof',
      narration:
        'Dual-mode simulation benchmarks prove AI superiority: -71.6% net corridor delay reduction, 100% P1 schedule protection, and zero secondary deadlocks.',
      highlightIcon: <BarChart3 size={18} className="text-green" />,
      action: () => {
        setActiveTab('analytics');
      },
    },
  ];

  // Execute step action on change
  useEffect(() => {
    if (isDemoMode && steps[currentStep]) {
      steps[currentStep].action();
    }
  }, [currentStep, isDemoMode]);

  // Autoplay timer: advances every 7.5 seconds
  useEffect(() => {
    if (!isDemoMode || !isAutoplay) return;

    const timer = setTimeout(() => {
      if (currentStep < steps.length - 1) {
        setCurrentStep((prev) => prev + 1);
      } else {
        setIsAutoplay(false); // Finished loop
      }
    }, 7500);

    return () => clearTimeout(timer);
  }, [currentStep, isAutoplay, isDemoMode, steps.length]);

  if (!isDemoMode) return null;

  const current = steps[currentStep];

  return (
    <aside aria-label="Interactive Presentation Walkthrough" className="demo-floating-controller animate-slide-up">
      <div className="demo-header">
        <div className="demo-title-group">
          <MonitorPlay size={16} className="text-brand" />
          <span className="demo-title">Presentation Demo Autoplay</span>
          <span className="demo-badge">{current.badge}</span>
        </div>

        <div className="demo-window-controls">
          <button
            className="demo-btn-icon"
            onClick={() => setIsAutoplay(!isAutoplay)}
            title={isAutoplay ? 'Pause Autoplay' : 'Resume Autoplay'}
          >
            {isAutoplay ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            className="demo-btn-icon"
            onClick={() => {
              setIsDemoMode(false);
              resetSimulation.mutate();
            }}
            title="Exit Demo Mode"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      <div className="demo-body">
        <div className="demo-icon-wrap">{current.highlightIcon}</div>
        <div className="demo-content">
          <h4 className="demo-step-heading">{current.title}</h4>
          <p className="demo-step-narration">{current.narration}</p>
        </div>
      </div>

      <div className="demo-footer">
        <div className="demo-progress-dots">
          {steps.map((_, i) => (
            <button
              key={i}
              type="button"
              className={`dot-btn ${i === currentStep ? 'dot-active' : ''}`}
              onClick={() => {
                setCurrentStep(i);
                setIsAutoplay(false);
              }}
              aria-label={`Jump to presentation step ${i + 1} of ${steps.length}`}
              aria-current={i === currentStep ? 'step' : undefined}
            />
          ))}
        </div>

        <div className="demo-nav-btns">
          <button
            className="demo-nav-btn"
            disabled={currentStep === 0}
            onClick={() => {
              setCurrentStep((p) => Math.max(0, p - 1));
              setIsAutoplay(false);
            }}
          >
            <ChevronLeft size={14} /> Prev
          </button>

          <span className="step-counter">
            {currentStep + 1} / {steps.length}
          </span>

          <button
            className="demo-nav-btn btn-primary"
            disabled={currentStep === steps.length - 1}
            onClick={() => {
              setCurrentStep((p) => Math.min(steps.length - 1, p + 1));
              setIsAutoplay(false);
            }}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
};
