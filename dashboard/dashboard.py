import sqlite3
from flask import Flask, jsonify, render_template_string
import os

app = Flask(__name__)

# We embed the HTML directly in the Python file so it is a single runnable script!
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Grid Command Center</title>
    <!-- Load Tailwind CSS for beautiful styling -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Load FontAwesome for sort icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Inter', sans-serif; }
        .glass-panel { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid #334155; }
        th { cursor: pointer; user-select: none; transition: color 0.2s; }
        th:hover { color: #38bdf8; }
        .live-dot { animation: pulse 2s infinite; }
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }
    </style>
</head>
<body class="min-h-screen p-6">
    
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
                    ⚡ Smart Grid Command Center
                </h1>
                <p class="text-slate-400 mt-2">Secure Edge Database Monitoring</p>
            </div>
            <div class="flex items-center space-x-2 bg-slate-800 px-4 py-2 rounded-full border border-slate-700">
                <div class="w-3 h-3 bg-green-500 rounded-full live-dot"></div>
                <span class="text-green-400 font-semibold text-sm">LIVE SYNC ACTIVE</span>
            </div>
        </div>

        <!-- Dashboard Widgets -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="glass-panel p-6 rounded-xl">
                <h3 class="text-slate-400 text-sm font-semibold mb-1">Active Meters</h3>
                <p class="text-4xl font-bold text-white" id="meterCount">--</p>
            </div>
            <div class="glass-panel p-6 rounded-xl">
                <h3 class="text-slate-400 text-sm font-semibold mb-1">Total Power Draw (kW)</h3>
                <p class="text-4xl font-bold text-cyan-400" id="totalPower">--</p>
            </div>
            <div class="glass-panel p-6 rounded-xl">
                <h3 class="text-slate-400 text-sm font-semibold mb-1">Database Records Displayed</h3>
                <p class="text-4xl font-bold text-blue-400" id="recordCount">--</p>
            </div>
        </div>

        <!-- Toolbar (Search) -->
        <div class="glass-panel p-4 rounded-t-xl border-b-0 flex justify-between items-center bg-slate-800">
            <div class="relative w-72">
                <i class="fa-solid fa-search absolute left-3 top-3.5 text-slate-400"></i>
                <input type="text" id="searchInput" placeholder="Search by Meter ID..." 
                    class="w-full bg-slate-900 border border-slate-700 text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors">
            </div>
            <div class="text-slate-400 text-sm">
                Auto-refreshing every <span class="font-bold text-white">2s</span>
            </div>
        </div>

        <!-- Data Table -->
        <div class="glass-panel rounded-b-xl overflow-hidden shadow-2xl">
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm whitespace-nowrap">
                    <thead class="bg-slate-900/50 text-slate-300 uppercase tracking-wider text-xs border-b border-slate-700">
                        <tr>
                            <th class="px-6 py-4 font-semibold" onclick="setSort('id')">Record ID <i class="fa-solid fa-sort ml-1"></i></th>
                            <th class="px-6 py-4 font-semibold" onclick="setSort('timestamp')">Timestamp <i class="fa-solid fa-sort ml-1"></i></th>
                            <th class="px-6 py-4 font-semibold" onclick="setSort('meter_id')">Meter ID <i class="fa-solid fa-sort ml-1"></i></th>
                            <th class="px-6 py-4 font-semibold" onclick="setSort('voltage')">Voltage (V) <i class="fa-solid fa-sort ml-1"></i></th>
                            <th class="px-6 py-4 font-semibold" onclick="setSort('current')">Current (A) <i class="fa-solid fa-sort ml-1"></i></th>
                            <th class="px-6 py-4 font-semibold" onclick="setSort('power_kW')">Power (kW) <i class="fa-solid fa-sort ml-1"></i></th>
                            <th class="px-6 py-4 font-semibold" onclick="setSort('units_kWh')">Total Units (kWh) <i class="fa-solid fa-sort ml-1"></i></th>
                        </tr>
                    </thead>
                    <tbody id="tableBody" class="divide-y divide-slate-700/50">
                        <!-- Data injected via JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let rawData = [];
        let sortCol = 'id';
        let sortDesc = true;

        // Fetch data from our Python Flask API
        async function fetchTelemetry() {
            try {
                const response = await fetch('/api/data');
                if (!response.ok) {
                    throw new Error(`Server returned status: ${response.status}`);
                }
                const result = await response.json();
                
                if (result.error) {
                    throw new Error(result.error);
                }
                
                rawData = result;
                renderTable();
            } catch (error) {
                console.error("Error fetching data:", error);
                const tbody = document.getElementById('tableBody');
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="px-6 py-8 text-center text-red-500 font-bold">
                            <i class="fa-solid fa-triangle-exclamation text-2xl mb-2"></i><br>
                            Error communicating with the Python server:<br>${error.message}
                        </td>
                    </tr>
                `;
            }
        }

        // Change sorting column and direction
        function setSort(col) {
            if (sortCol === col) {
                sortDesc = !sortDesc;
            } else {
                sortCol = col;
                sortDesc = true; // Default to descending when clicking a new column
            }
            renderTable();
        }

        // Render the HTML table dynamically
        function renderTable() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            // 1. Filter by Meter ID
            let filteredData = rawData.filter(row => 
                row.meter_id.toLowerCase().includes(searchTerm)
            );

            // 2. Sort the data
            filteredData.sort((a, b) => {
                let valA = a[sortCol] !== null ? a[sortCol] : '';
                let valB = b[sortCol] !== null ? b[sortCol] : '';
                
                // Handle string comparison for meter_id
                if (typeof valA === 'string') valA = valA.toLowerCase();
                if (typeof valB === 'string') valB = valB.toLowerCase();

                if (valA < valB) return sortDesc ? 1 : -1;
                if (valA > valB) return sortDesc ? -1 : 1;
                return 0;
            });

            // 3. Update top widgets
            const uniqueMeters = new Set(filteredData.map(d => d.meter_id)).size;
            
            // Fix: Calculate sum safely
            let totalPower = 0;
            filteredData.forEach(d => {
                if (d.power_kW && !isNaN(d.power_kW)) {
                    totalPower += parseFloat(d.power_kW);
                }
            });

            document.getElementById('meterCount').innerText = uniqueMeters;
            document.getElementById('totalPower').innerText = totalPower.toFixed(2);
            document.getElementById('recordCount').innerText = filteredData.length;

            // 4. Build Table Rows
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = ''; // Clear old rows

            if (filteredData.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="px-6 py-8 text-center text-slate-400">
                            <i class="fa-solid fa-satellite-dish text-2xl mb-2 animate-pulse text-slate-500"></i><br>
                            No telemetry data found.<br>
                            Ensure the <b>Gateway</b> and <b>Smart Meters</b> are running to populate the database.
                        </td>
                    </tr>
                `;
                return;
            }

            filteredData.forEach(row => {
                // Convert Unix timestamp to readable local time
                const timeStr = new Date(row.timestamp * 1000).toLocaleTimeString();
                
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-800/50 transition-colors";
                
                tr.innerHTML = `
                    <td class="px-6 py-3 text-slate-400">#${row.id}</td>
                    <td class="px-6 py-3 text-slate-300 font-mono">${timeStr}</td>
                    <td class="px-6 py-3 font-semibold text-cyan-400">${row.meter_id || 'UNKNOWN'}</td>
                    <td class="px-6 py-3 text-slate-300">${(row.voltage || 0).toFixed(2)}</td>
                    <td class="px-6 py-3 text-slate-300">${(row.current || 0).toFixed(2)}</td>
                    <td class="px-6 py-3 font-bold text-amber-400">${(row.power_kW || 0).toFixed(2)}</td>
                    <td class="px-6 py-3 text-slate-300">${(row.units_kWh || 0).toFixed(2)}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Search input event listener
        document.getElementById('searchInput').addEventListener('input', renderTable);

        // Fetch immediately, then loop every 2 seconds
        fetchTelemetry();
        setInterval(fetchTelemetry, 2000);
    </script>
</body>
</html>
"""

def get_db_connection():
    # Ultra-smart database finder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check all possible locations where the database might have been created
    possible_paths = [
        os.path.join(base_dir, 'secure_grid.db'),
        os.path.join(base_dir, 'gateway', 'secure_grid.db'),
        os.path.join(base_dir, '..', 'secure_grid.db')
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
            
    if not db_path:
        db_path = possible_paths[0] # Fallback if none exist
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, db_path

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    try:
        conn, _ = get_db_connection()
        rows = conn.execute('SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT 250').fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except sqlite3.OperationalError as e:
        return jsonify({"error": f"Database exists but table missing: {e}"})
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"})

if __name__ == '__main__':
    print("\n=======================================================")
    print("🔍 RUNNING SYSTEM DIAGNOSTICS...")
    
    try:
        conn, path = get_db_connection()
        if os.path.exists(path):
            print(f"✅ DATABASE FOUND AT: {path}")
            try:
                count = conn.execute('SELECT COUNT(*) FROM telemetry').fetchone()[0]
                print(f"📊 DATA CHECK: Found {count} rows in the database.")
                if count == 0:
                    print("⚠️ WARNING: The database is completely empty! Ensure Gateway and Meters are running.")
            except sqlite3.OperationalError:
                print("❌ ERROR: Database file exists, but the 'telemetry' table is missing.")
        else:
            print(f"❌ DATABASE NOT FOUND! Searched everywhere. Is the Gateway running?")
        conn.close()
    except Exception as e:
        print(f"❌ DIAGNOSTIC FAILED: {e}")
        
    print("\n🚀 BOOTING SMART GRID COMMAND CENTER...")
    print("🌐 Open your web browser to: http://127.0.0.1:5000")
    print("=======================================================\n")
    
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host='0.0.0.0', port=5000, debug=False)