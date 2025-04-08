/**
 * Format large numbers for display
 * @param {number} num - Number to format
 * @returns {string} - Formatted string
 */
function formatLargeNumber(num) {
    if (num >= 1000000000) {
        return (num / 1000000000).toFixed(1) + 'B';
    }
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * Create a revenue chart for a protocol
 * @param {string} chartId - ID of the canvas element
 * @param {Array} data - Revenue data from API
 */
function createRevenueChart(chartId, data) {
    if (!data || data.length === 0) {
        document.getElementById(chartId).parentElement.innerHTML = 
            '<div class="alert alert-info">No revenue data available</div>';
        return;
    }
    
    // Sort data by month (chronological order)
    data.sort((a, b) => new Date(a.month) - new Date(b.month));
    
    // Extract labels (months) and revenue values
    const labels = data.map(item => {
        const date = new Date(item.month);
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    });
    
    // Group data by source
    const sources = [...new Set(data.map(item => item.source))];
    const datasets = sources.map(source => {
        const color = getColorForSource(source);
        const sourceData = data.filter(item => item.source === source);
        
        return {
            label: source.charAt(0).toUpperCase() + source.slice(1),
            data: sourceData.map(item => item.revenue),
            backgroundColor: color,
            borderColor: color,
            borderWidth: 2
        };
    });
    
    // Create the chart
    const ctx = document.getElementById(chartId).getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += '$' + formatLargeNumber(context.raw);
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + formatLargeNumber(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create a user metrics chart for a protocol
 * @param {string} chartId - ID of the canvas element
 * @param {Array} data - User metrics data from API
 */
function createUserMetricsChart(chartId, data) {
    if (!data || data.length === 0) {
        document.getElementById(chartId).parentElement.innerHTML = 
            '<div class="alert alert-info">No user metrics data available</div>';
        return;
    }
    
    // Sort data by month (chronological order)
    data.sort((a, b) => new Date(a.month) - new Date(b.month));
    
    // Extract labels (months)
    const labels = data.map(item => {
        const date = new Date(item.month);
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    });
    
    // Create the chart with multiple axes
    const ctx = document.getElementById(chartId).getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Active Addresses',
                    data: data.map(item => item.active_addresses),
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    yAxisID: 'y',
                    tension: 0.1
                },
                {
                    label: 'Transaction Count',
                    data: data.map(item => item.transaction_count),
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    yAxisID: 'y1',
                    tension: 0.1
                },
                {
                    label: 'Transaction Volume ($)',
                    data: data.map(item => item.transaction_volume),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    yAxisID: 'y2',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.datasetIndex === 2) {
                                label += '$' + formatLargeNumber(context.raw);
                            } else {
                                label += formatLargeNumber(context.raw);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Active Addresses'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatLargeNumber(value);
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Transaction Count'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatLargeNumber(value);
                        }
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                },
                y2: {
                    type: 'linear',
                    display: false,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Transaction Volume ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + formatLargeNumber(value);
                        }
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    });
}

/**
 * Get a color for a revenue source
 * @param {string} source - Source name
 * @returns {string} - Color for the source
 */
function getColorForSource(source) {
    const colorMap = {
        'total': 'rgba(54, 162, 235, 0.8)',
        'vrf': 'rgba(255, 99, 132, 0.8)',
        'automation': 'rgba(75, 192, 192, 0.8)',
        'fm': 'rgba(255, 159, 64, 0.8)',
        'ocr': 'rgba(153, 102, 255, 0.8)',
        'ccip': 'rgba(201, 203, 207, 0.8)',
        'v2': 'rgba(255, 99, 132, 0.8)',
        'v3': 'rgba(54, 162, 235, 0.8)'
    };
    
    return colorMap[source.toLowerCase()] || 'rgba(54, 162, 235, 0.8)';
}

/**
 * Create a radar chart for the four scores
 * @param {string} chartId - ID of the canvas element
 * @param {Object} scores - Score data object
 */
function createScoreRadarChart(chartId, scores) {
    const ctx = document.getElementById(chartId).getContext('2d');
    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: [
                'Earnings Quality',
                'User Growth',
                'Fair Value',
                'Safety'
            ],
            datasets: [{
                label: 'Protocol Scores',
                data: [
                    scores.eqs,
                    scores.ugs,
                    scores.fvs,
                    scores.ss
                ],
                fill: true,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgb(54, 162, 235)',
                pointBackgroundColor: 'rgb(54, 162, 235)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            scales: {
                r: {
                    angleLines: {
                        display: true
                    },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            }
        }
    });
}

/**
 * Create a bar chart for category comparison
 * @param {string} chartId - ID of the canvas element
 * @param {Array} categories - Category data
 */
function createCategoryComparisonChart(chartId, categories) {
    const ctx = document.getElementById(chartId).getContext('2d');
    
    // Extract data
    const labels = categories.map(cat => cat.name);
    const howScores = categories.map(cat => cat.avg_how3);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average How3 Score',
                data: howScores,
                backgroundColor: 'rgba(54, 162, 235, 0.8)',
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
            }
        }
    });
}