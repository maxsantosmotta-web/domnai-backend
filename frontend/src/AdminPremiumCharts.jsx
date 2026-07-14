import React, { useId, useMemo, useState } from 'react';

const CHART_COLORS = ['#f4c95d', '#3fd7ff', '#ff5cc8', '#64e6a6', '#9b82ff', '#ff9f5a', '#ff657f'];

function safeNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function defaultFormatter(value) {
  return safeNumber(value).toLocaleString('pt-BR');
}

function chartPath(points) {
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
}

export function InteractiveLineChart({
  data = [],
  title,
  subtitle,
  valueFormatter = defaultFormatter,
  primaryLabel = 'Valor',
  secondaryLabel = '',
  emptyLabel = 'Sem dados suficientes',
}) {
  const gradientId = useId().replaceAll(':', '');
  const [activeIndex, setActiveIndex] = useState(null);
  const width = 760;
  const height = 250;
  const padding = { top: 24, right: 24, bottom: 42, left: 42 };

  const normalized = useMemo(() => data.map((item, index) => ({
    label: String(item?.label || index + 1),
    value: safeNumber(item?.value),
    secondaryValue: item?.secondaryValue === null || item?.secondaryValue === undefined
      ? null
      : safeNumber(item.secondaryValue),
  })), [data]);

  const hasSecondary = normalized.some((item) => item.secondaryValue !== null);
  const maxValue = Math.max(
    1,
    ...normalized.map((item) => item.value),
    ...normalized.map((item) => item.secondaryValue ?? 0),
  );
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const divisor = Math.max(1, normalized.length - 1);

  const points = normalized.map((item, index) => ({
    ...item,
    x: padding.left + (index / divisor) * innerWidth,
    y: padding.top + innerHeight - (item.value / maxValue) * innerHeight,
    secondaryY: item.secondaryValue === null
      ? null
      : padding.top + innerHeight - (item.secondaryValue / maxValue) * innerHeight,
  }));
  const secondaryPoints = points.filter((point) => point.secondaryY !== null).map((point) => ({ ...point, y: point.secondaryY }));
  const primaryPath = chartPath(points);
  const secondaryPath = chartPath(secondaryPoints);
  const areaPath = points.length
    ? `${primaryPath} L ${points[points.length - 1].x} ${padding.top + innerHeight} L ${points[0].x} ${padding.top + innerHeight} Z`
    : '';
  const resolvedIndex = activeIndex === null ? Math.max(0, points.length - 1) : Math.min(activeIndex, Math.max(0, points.length - 1));
  const active = points[resolvedIndex];

  function selectFromPointer(event) {
    if (!points.length) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / Math.max(1, rect.width)));
    setActiveIndex(Math.round(ratio * (points.length - 1)));
  }

  return (
    <section className="domnai-premium-chart-card line-chart-card">
      <header>
        <div><span>{subtitle}</span><strong>{title}</strong></div>
        {active ? (
          <div className="domnai-chart-current">
            <small>{active.label}</small>
            <strong>{valueFormatter(active.value)}</strong>
          </div>
        ) : null}
      </header>

      {points.length ? (
        <div className="domnai-line-chart-stage">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label={title}
            onPointerDown={selectFromPointer}
            onPointerMove={selectFromPointer}
            onPointerLeave={() => setActiveIndex(null)}
          >
            <defs>
              <linearGradient id={`${gradientId}-area`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f4c95d" stopOpacity="0.34" />
                <stop offset="100%" stopColor="#f4c95d" stopOpacity="0" />
              </linearGradient>
              <linearGradient id={`${gradientId}-line`} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#3fd7ff" />
                <stop offset="50%" stopColor="#f4c95d" />
                <stop offset="100%" stopColor="#ff5cc8" />
              </linearGradient>
            </defs>

            {[0, 0.25, 0.5, 0.75, 1].map((step) => {
              const y = padding.top + innerHeight - (step * innerHeight);
              return <line key={step} x1={padding.left} y1={y} x2={width - padding.right} y2={y} className="premium-grid-line" />;
            })}

            {areaPath ? <path d={areaPath} fill={`url(#${gradientId}-area)`} className="premium-chart-area" /> : null}
            {primaryPath ? (
              <path
                key={normalized.map((item) => item.value).join('-')}
                d={primaryPath}
                fill="none"
                stroke={`url(#${gradientId}-line)`}
                className="premium-chart-line"
                pathLength="1"
              />
            ) : null}
            {secondaryPath ? (
              <path
                key={normalized.map((item) => item.secondaryValue ?? '').join('-')}
                d={secondaryPath}
                fill="none"
                className="premium-chart-line secondary"
                pathLength="1"
              />
            ) : null}

            {active ? (
              <g className="premium-active-marker">
                <line x1={active.x} y1={padding.top} x2={active.x} y2={padding.top + innerHeight} />
                <circle cx={active.x} cy={active.y} r="7" />
                {active.secondaryY !== null ? <circle className="secondary" cx={active.x} cy={active.secondaryY} r="6" /> : null}
              </g>
            ) : null}

            {[0, Math.floor((points.length - 1) / 2), points.length - 1]
              .filter((index, position, all) => index >= 0 && all.indexOf(index) === position)
              .map((index) => (
                <text key={index} x={points[index].x} y={height - 13} textAnchor="middle" className="premium-axis-label">
                  {points[index].label}
                </text>
              ))}
          </svg>

          {active ? (
            <div className="domnai-chart-tooltip" style={{ '--tooltip-left': `${(active.x / width) * 100}%` }}>
              <span>{active.label}</span>
              <strong><i className="primary" />{primaryLabel}: {valueFormatter(active.value)}</strong>
              {hasSecondary && active.secondaryValue !== null ? (
                <strong><i className="secondary" />{secondaryLabel || 'Comparativo'}: {valueFormatter(active.secondaryValue)}</strong>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="domnai-chart-empty">{emptyLabel}</div>
      )}
    </section>
  );
}

export function InteractiveBarChart({
  data = [],
  title,
  subtitle,
  valueFormatter = defaultFormatter,
  emptyLabel = 'Sem dados registrados',
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const normalized = useMemo(() => data.map((item, index) => ({
    label: String(item?.label || index + 1),
    value: safeNumber(item?.value),
    color: item?.color || CHART_COLORS[index % CHART_COLORS.length],
  })), [data]);
  const maxValue = Math.max(1, ...normalized.map((item) => item.value));
  const active = normalized[Math.min(activeIndex, Math.max(0, normalized.length - 1))];

  return (
    <section className="domnai-premium-chart-card bar-chart-card">
      <header>
        <div><span>{subtitle}</span><strong>{title}</strong></div>
        {active ? <div className="domnai-chart-current"><small>{active.label}</small><strong>{valueFormatter(active.value)}</strong></div> : null}
      </header>
      {normalized.length ? (
        <div className="domnai-premium-bars">
          {normalized.map((item, index) => (
            <div
              className={`domnai-premium-bar-row${activeIndex === index ? ' is-active' : ''}`}
              role="button"
              tabIndex="0"
              aria-label={`${item.label}: ${valueFormatter(item.value)}`}
              onPointerDown={() => setActiveIndex(index)}
              onPointerEnter={() => setActiveIndex(index)}
              onFocus={() => setActiveIndex(index)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') setActiveIndex(index);
              }}
              key={item.label}
            >
              <div><span>{item.label}</span><strong>{valueFormatter(item.value)}</strong></div>
              <div className="premium-bar-track">
                <span style={{ '--bar-width': `${Math.max(item.value > 0 ? 3 : 0, (item.value / maxValue) * 100)}%`, '--bar-color': item.color }} />
              </div>
            </div>
          ))}
        </div>
      ) : <div className="domnai-chart-empty">{emptyLabel}</div>}
    </section>
  );
}

export function InteractiveDonutChart({
  data = [],
  title,
  subtitle,
  valueFormatter = defaultFormatter,
  centerLabel = 'Total',
  emptyLabel = 'Sem distribuição disponível',
}) {
  const [activeIndex, setActiveIndex] = useState(null);
  const normalized = useMemo(() => data.map((item, index) => ({
    label: String(item?.label || index + 1),
    value: Math.max(0, safeNumber(item?.value)),
    color: item?.color || CHART_COLORS[index % CHART_COLORS.length],
  })), [data]);
  const total = normalized.reduce((sum, item) => sum + item.value, 0);
  let cursor = 0;
  const segments = normalized.map((item) => {
    const start = total > 0 ? (cursor / total) * 360 : 0;
    cursor += item.value;
    const end = total > 0 ? (cursor / total) * 360 : 0;
    return `${item.color} ${start}deg ${end}deg`;
  });
  const active = activeIndex === null ? null : normalized[activeIndex];
  const gradient = total > 0 ? `conic-gradient(${segments.join(', ')})` : 'conic-gradient(#252525 0deg 360deg)';

  return (
    <section className="domnai-premium-chart-card donut-chart-card">
      <header><div><span>{subtitle}</span><strong>{title}</strong></div></header>
      {normalized.length ? (
        <div className="domnai-donut-layout">
          <div className="domnai-premium-donut" style={{ '--donut-fill': gradient }}>
            <div>
              <small>{active?.label || centerLabel}</small>
              <strong>{valueFormatter(active?.value ?? total)}</strong>
            </div>
          </div>
          <div className="domnai-donut-legend">
            {normalized.map((item, index) => (
              <div
                role="button"
                tabIndex="0"
                className={activeIndex === index ? 'is-active' : ''}
                onPointerDown={() => setActiveIndex(index)}
                onPointerEnter={() => setActiveIndex(index)}
                onPointerLeave={() => setActiveIndex(null)}
                onFocus={() => setActiveIndex(index)}
                onBlur={() => setActiveIndex(null)}
                key={item.label}
              >
                <i style={{ background: item.color }} />
                <span>{item.label}</span>
                <strong>{valueFormatter(item.value)}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : <div className="domnai-chart-empty">{emptyLabel}</div>}
    </section>
  );
}
