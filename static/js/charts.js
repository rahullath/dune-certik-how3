/**
 * Charts.js - Chart configuration and utilities for How3.io
 * Contains helper functions for creating and styling charts across the application
 */

// Chart color palette
const chartColors = {
    primary: 'rgba(13, 110, 253, 0.7)',
    info: 'rgba(23, 162, 184, 0.7)',
    success: 'rgba(40, 167, 69, 0.7)',
    warning: 'rgba(255, 193, 7, 0.7)',
    danger: 'rgba(220, 53, 69, 0.7)',
    secondary: 'rgba(108, 117, 125, 0.7)',
    dark: 'rgba(52, 58, 64, 0.7)',
    light: 'rgba(248, 249, 250, 0.7)',
    // Additional colors for datasets
    blue: 'rgba(54, 162, 235, 0.7)',
    red: 'rgba(255, 99, 132, 0.7)',
    yellow: 'rgba(255, 206, 86, 0.7)',
    green: 'rgba(75, 192, 192, 0.7)',
    purple: 'rgba(153, 102, 255, 0.7)',
    orange: 'rgba(255, 159, 64, 0.7)'
};

// Chart border colors (solid versions of the above)
const chartBorderColors = {
    primary: 'rgb(13, 110, 253)',
    info: 'rgb(23, 162, 184)',
    success: 'rgb(40, 167, 69)',
    warning: 'rgb(255, 193, 7)',
    danger: 'rgb(220, 53, 69)',
    secondary: 'rgb(108, 117, 125)',
    dark: 'rgb(52, 58, 64)',
    light: 'rgb(248, 249, 250)',
    // Additional colors for datasets
    blue: 'rgb(54, 162, 235)',
    red: 'rgb(255, 99, 132)',
    yellow: 'rgb(255, 206, 86)',
    green: 'rgb(75, 192, 192)',
    purple: 'rgb(153, 102, 255)',
    orange: 'rgb(255, 159, 64)'
};

/**
 * Get a chart color by index (with optional alpha value)
 * @param {number} index - Index of the color
 * @param {number} alpha - Optional alpha value (0-1)
 * @returns {string} - RGBA color string
 */
function getChartColor(index, alpha = 0.7) {
    const colors = [
        `rgba(54, 162, 235, ${alpha})`,
        `rgba(255, 99, 132, ${alpha})`,
        `rgba(255, 206, 86, ${alpha})`,
        `rgba(75, 192, 192, ${alpha})`,
        `rgba(153, 102, 255, ${alpha})`,
        `rgba(255, 159, 64, ${alpha})`
    ];
    return colors[index % colors.length];
}

/**
 * Get a chart border color by index
 * @param {number} index - Index of the color
 * @returns {string} - RGB color string
 */
function getChartBorderColor(index) {
    const colors = [
        'rgb(54, 162, 235)',
        'rgb(255, 99, 132)',
        'rgb(255, 206, 86)',
        'rgb(75, 192, 192)',
        'rgb(153, 102, 255)',
        'rgb(255, 159, 64)'
    ];
    return colors[index % colors.length];
}

/**
 * Format numbers for display on charts
 * @param {number} num - Number to format
 * @param {boolean} prefix - Whether to include currency prefix
 * @returns {string} - Formatted number
 */
function formatNumber(num, prefix = false) {
    if (num === null || num === undefined || isNaN(num)) {
        return 'N/A';
    }

    const sign = num < 0 ? '-' : '';
    const absNum = Math.abs(num);
    
    let formatted;
    if (absNum >= 1000000000) {
        formatted = (absNum / 1000000000).toFixed(1) + 'B';
    } else if (absNum >= 1000000) {
        formatted = (absNum / 1000000).toFixed(1) + 'M';
    } else if (absNum >= 1000) {
        formatted = (absNum / 1000).toFixed(1) + 'K';
    } else {
        formatted = absNum.toFixed(0);
    }
    
    return prefix ? sign + '$' + formatted : sign + formatted;
}

/**
 * Create a revenue chart configuration
 * @param {object} chartData - Chart data with labels and datasets
 * @returns {object} - Chart.js configuration object
 */
function createRevenueChartConfig(chartData) {
    return {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Monthly Revenue by Source'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': $' + formatNumber(context.raw);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + formatNumber(value);
                        }
                    }
                }
            }
        }
    };
}

/**
 * Create a user metrics chart configuration
 * @param {object} chartData - Chart data with labels and metrics
 * @returns {object} - Chart.js configuration object
 */
function createUserMetricsChartConfig(chartData) {
    return {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'Active Addresses',
                    data: chartData.active_addresses,
                    backgroundColor: chartColors.blue,
                    borderColor: chartBorderColors.blue,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Transaction Count',
                    data: chartData.transaction_count,
                    backgroundColor: chartColors.red,
                    borderColor: chartBorderColors.red,
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Monthly User Metrics'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let value = context.raw;
                            return context.dataset.label + ': ' + formatNumber(value);
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
                            return formatNumber(value);
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
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    };
}

/**
 * Create a radar chart configuration for protocol comparison
 * @param {array} protocols - Array of protocol data objects
 * @returns {object} - Chart.js configuration object
 */
function createRadarChartConfig(protocols) {
    const datasets = protocols.map((protocol, index) => {
        return {
            label: protocol.name,
            data: [
                protocol.scores.eqs,
                protocol.scores.ugs,
                protocol.scores.fvs,
                protocol.scores.ss
            ],
            backgroundColor: getChartColor(index, 0.2),
            borderColor: getChartBorderColor(index),
            pointBackgroundColor: getChartBorderColor(index),
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: getChartBorderColor(index)
        };
    });
    
    return {
        type: 'radar',
        data: {
            labels: ['EQS', 'UGS', 'FVS', 'SS'],
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Score Comparison'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toFixed(1);
                        }
                    }
                }
            },
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
    };
}

/**
 * Create a score distribution chart configuration
 * @param {array} data - Array of score data
 * @param {string} scoreType - Type of score (eqs, ugs, fvs, ss)
 * @returns {object} - Chart.js configuration object
 */
function createScoreDistributionChart(data, scoreType) {
    // Determine color based on score type
    let color;
    let title;
    
    switch (scoreType) {
        case 'eqs':
            color = chartColors.info;
            title = 'Earnings Quality Score Distribution';
            break;
        case 'ugs':
            color = chartColors.success;
            title = 'User Growth Score Distribution';
            break;
        case 'fvs':
            color = chartColors.warning;
            title = 'Fair Value Score Distribution';
            break;
        case 'ss':
            color = chartColors.danger;
            title = 'Safety Score Distribution';
            break;
        default:
            color = chartColors.primary;
            title = 'Score Distribution';
    }
    
    // Create histogram data
    const binSize = 10;
    const bins = Array(11).fill(0); // 0-10, 10-20, ..., 90-100
    
    data.forEach(score => {
        const binIndex = Math.min(Math.floor(score / binSize), 10);
        bins[binIndex]++;
    });
    
    const labels = [];
    for (let i = 0; i < 10; i++) {
        labels.push(`${i * 10}-${(i + 1) * 10}`);
    }
    labels.push('100');
    
    return {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Protocols',
                data: bins,
                backgroundColor: color,
                borderColor: color.replace('0.7', '1'),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: title
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Protocols'
                    },
                    ticks: {
                        stepSize: 1
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Score Range'
                    }
                }
            }
        }
    };
}
