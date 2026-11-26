const { useEffect, useRef } = window.React;
const html = window.htm.bind(window.React.createElement);

export function AbsorptionChart({ profile, t }) {
  const canvasRef = useRef(null);
  const chartInstanceRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !profile || !window.Chart) return;

    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
      chartInstanceRef.current = null;
    }

    const isElevation = profile.curve_mode === "elevation_toxicity";
    const interferedColor = isElevation ? "#9a4708" : "#b42318";
    const interferedFill = isElevation ? "rgba(154, 71, 8, 0.08)" : "rgba(180, 35, 24, 0.08)";
    const labels = profile.time_points_hours.map((h) => (Number.isInteger(h) ? `${h}h` : `${h}h`));
    const yMax = isElevation ? 165 : 120;

    const thresholdPlugin = {
      id: "clinicalThresholds",
      beforeDatasetsDraw(chart) {
        const { ctx, chartArea, scales } = chart;
        if (!chartArea || !scales.y) return;
        ctx.save();

        const drawBand = (value, strokeColor, labelText) => {
          const y = scales.y.getPixelForValue(value);
          if (y < chartArea.top || y > chartArea.bottom) return;
          ctx.beginPath();
          ctx.setLineDash([4, 4]);
          ctx.strokeStyle = strokeColor;
          ctx.lineWidth = 1;
          ctx.moveTo(chartArea.left, y);
          ctx.lineTo(chartArea.right, y);
          ctx.stroke();

          ctx.setLineDash([]);
          ctx.fillStyle = strokeColor;
          ctx.font = '500 11px "IBM Plex Mono", Consolas, monospace';
          ctx.textAlign = "right";
          ctx.fillText(labelText, chartArea.right - 4, y - 5);
        };

        drawBand(profile.therapeutic_floor_pct, "rgba(22, 101, 52, 0.65)", t.curve.legend_threshold);
        if (isElevation) {
          drawBand(profile.safety_ceiling_pct, "rgba(154, 71, 8, 0.72)", t.curve.legend_ceiling);
        }
        ctx.restore();
      },
    };

    chartInstanceRef.current = new window.Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: t.curve.legend_normal,
            data: profile.normal_series_pct,
            borderColor: "#1f1b16",
            backgroundColor: "rgba(31, 27, 22, 0.03)",
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.32,
            fill: false,
          },
          {
            label: t.curve.legend_interfered,
            data: profile.interfered_series_pct,
            borderColor: interferedColor,
            backgroundColor: interferedFill,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5,
            tension: 0.32,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 240 },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            position: "top",
            align: "start",
            labels: {
              boxWidth: 12,
              boxHeight: 2,
              color: "#534a40",
              font: { size: 12, weight: "500" },
              padding: 16,
            },
          },
          tooltip: {
            backgroundColor: "#1f1b16",
            titleColor: "#fdfbf7",
            bodyColor: "#fdfbf7",
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.parsed.y).toFixed(1)}%`,
            },
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: t.curve.axis_x,
              color: "#6c6358",
              font: { size: 12, weight: "500" },
            },
            grid: { display: false },
            ticks: {
              color: "#6c6358",
              maxTicksLimit: 13,
              callback: function (_, idx) {
                const val = profile.time_points_hours[idx];
                return Number.isInteger(val) ? `${val}h` : null;
              },
              font: { family: '"IBM Plex Mono", Consolas, monospace', size: 11 },
            },
          },
          y: {
            min: 0,
            max: yMax,
            title: {
              display: true,
              text: t.curve.axis_y,
              color: "#6c6358",
              font: { size: 12, weight: "500" },
            },
            grid: { color: "rgba(31, 27, 22, 0.06)" },
            ticks: {
              stepSize: 25,
              color: "#6c6358",
              callback: (v) => `${v}%`,
              font: { family: '"IBM Plex Mono", Consolas, monospace', size: 11 },
            },
          },
        },
      },
      plugins: [thresholdPlugin],
    });

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
        chartInstanceRef.current = null;
      }
    };
  }, [profile, t]);

  return html`
    <div class="chart-canvas-wrap">
      <canvas ref=${canvasRef} aria-label=${t.curve.heading} />
    </div>
  `;
}
