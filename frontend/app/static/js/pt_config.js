// Shared configuration for pressure transducer plots
const PT_PLOT_CONFIG = {
    // Common layout settings
    layout: {
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        font: {
            family: 'Roboto, sans-serif',
            size: 12
        },
        margin: { t: 50, r: 20, b: 40, l: 50 }
    },

    // Common trace settings
    trace: {
        type: 'scatter',
        mode: 'lines',
        line: {
            width: 2,
            color: '#000'
        }
    },

    // Common axis settings
    axis: {
        title: {
            font: {
                family: 'Roboto, sans-serif',
                size: 12
            }
        },
        tickfont: {
            family: 'Roboto, sans-serif',
            size: 10
        },
        gridcolor: '#f0f0f0',
        zerolinecolor: '#f0f0f0'
    },

    // Common legend settings
    legend: {
        font: {
            family: 'Roboto, sans-serif',
            size: 10
        },
        bgcolor: 'rgba(255, 255, 255, 0.8)',
        bordercolor: '#f0f0f0',
        borderwidth: 1
    },

    // Common title settings
    title: {
        font: {
            family: 'Roboto, sans-serif',
            size: 16
        }
    },

    // Common hover settings
    hover: {
        mode: 'x unified',
        hoverlabel: {
            font: {
                family: 'Roboto, sans-serif',
                size: 10
            }
        }
    }
}; 