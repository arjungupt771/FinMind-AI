let chartInstances = {};

function destroyChart(key) {
  if (chartInstances[key]) {
    chartInstances[key].destroy();
    delete chartInstances[key];
  }
}

function basicOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#8B90A4', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#8B90A4', font: { size: 11 }, callback: (value) => `₹${value / 1000}k` }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };
}

export function renderCashflowChart(canvas, monthly) {
  destroyChart('cashflow');
  chartInstances.cashflow = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: monthly.map((item) => item.month),
      datasets: [
        { label: 'Income', data: monthly.map((item) => item.income), backgroundColor: 'rgba(78,205,196,0.4)', borderColor: '#4ECDC4', borderWidth: 1.5, borderRadius: 6 },
        { label: 'Expense', data: monthly.map((item) => item.expense), backgroundColor: 'rgba(124,106,247,0.4)', borderColor: '#7C6AF7', borderWidth: 1.5, borderRadius: 6 },
      ],
    },
    options: basicOptions(),
  });
}

export function renderCategoryChart(canvas, breakdown) {
  destroyChart('category');
  chartInstances.category = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: breakdown.map((item) => item.category),
      datasets: [{ data: breakdown.map((item) => item.amount), backgroundColor: breakdown.map((item) => item.color || '#7C6AF7') }],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#E8EAF0', boxWidth: 10 } } } },
  });
}

export function renderSavingsChart(canvas, savingsData) {
  destroyChart('savings');
  chartInstances.savings = new Chart(canvas, {
    type: 'line',
    data: {
      labels: savingsData.map((item) => item.month),
      datasets: [{ label: 'Savings', data: savingsData.map((item) => item.savings), borderColor: '#7C6AF7', backgroundColor: 'rgba(124,106,247,0.14)', borderWidth: 2, tension: 0.35, fill: true, pointRadius: 3 }],
    },
    options: basicOptions(),
  });
}
