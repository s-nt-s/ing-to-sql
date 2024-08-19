const DFL_RGB_COLOR = {
  red: {
    backgroundColor: "rgba(255, 99, 132, 0.2)",
    borderColor: "rgba(255, 99, 132, 1)",
  },
  blue: {
    backgroundColor: "rgba(54, 162, 235, 0.2)",
    borderColor: "rgba(54, 162, 235, 1)",
  },
  green: {
    backgroundColor: "rgb(60, 255, 60, 0.2)",
    borderColor: "rgb(60, 255, 60)",
  },
  yellow: {
    backgroundColor: "rgb(255,255,0, 0.2)",
    borderColor: "rgb(255,255,0)",
  },
  grey: {
    backgroundColor: "rgb(211,211,211, 0.2)",
    borderColor: "rgb(211,211,211)",
  },
};

function getCanvas(id) {
  let n = $.i(id);
  if (n == null) {
    console.error("#" + id + " no encontrado");
    return null;
  }
  if (n.tagName == "CANVAS") return n;
  const cnvs = n.getElementsByTagName("canvas");
  if (cnvs.length == 1) return cnvs[0];
  if (cnvs.length > 1) {
    console.error("#" + id + " canvas da demasiados resultados");
    return null;
  }
  console.debug("Se crea <canvas> en #" + id);
  n.insertAdjacentHTML("beforeend", "<canvas></canvas>");
  return n.getElementsByTagName("canvas")[0];
}

function frmtEur(n) {
  return n.toLocaleString("es-ES", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
    useGrouping: "always",
  });
}


function calStepSize(datasets, chart) {
  if (chart !=null) datasets = chart.data.datasets;
  const vals = datasets.flatMap((dataset, i) => {
    if (chart!=null && !chart.isDatasetVisible(i)) return [];
      return dataset.data;
  });
  const length = vals.length / datasets.length;

  let s;
  const steps = [10000, 1000];
  for (let i = 0; i < steps.length; i++) {
    s = steps[i];
    if (vals.filter((v) => v > s).length > length) return s;
  }
  return null;
}

function setChart(id, data) {
  const ctx = getCanvas(id);
  if (ctx == null) return null;
  const chrt = Chart.getChart(ctx);
  if (chrt == null) {
    if (data == null) return;
    new Chart(ctx, {
      type: "line",
      data: data,
      options: {
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          y: {
            ticks: {
              stepSize: calStepSize(data.datasets),
              callback: function (value, index, values) {
                const yScale = this.chart.scales.y;
                const stepSize = yScale.options.ticks.stepSize;

                console.log("Step size utilizado:", stepSize);
                if (stepSize>=1000 && (stepSize%1000==0)) {
                  return frmtEur(value/1000).replace("€", "k€");
                }
                return frmtEur(value);
              },
            },
          },
        },
        plugins: {
          tooltip: {
            titleAlign: "center",
            bodyAlign: "right",
            titleFont: {
              family: "monospace",
            },
            bodyFont: {
              family: "monospace",
            },
            footerFont: {
              family: "monospace",
            },
            callbacks: {
              label: (context) => " " + frmtEur(context.raw),
            },
          },
          legend: {
            onClick: (e, legendItem, legend) => {
              const index = legendItem.datasetIndex;
              const ci = legend.chart;
              const meta = ci.getDatasetMeta(index);

              meta.hidden = meta.hidden === null ? !ci.data.datasets[index].hidden : null;

              ci.options.scales.y.ticks.stepSize = calStepSize(ci.data.datasets, ci);

              ci.update();
            },
          },
        },
      },
    });
    return;
  }
  if (data == null) {
    chrt.destroy();
    return;
  }
  chrt.data = data;
  chrt.update();
}
