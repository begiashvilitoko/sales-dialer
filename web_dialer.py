import sqlite3
import datetime
import csv
import io
import urllib.parse
from flask import Flask, render_template_string, request, jsonify, Response

app = Flask(__name__)


# --- ბაზის ინიციალიზაცია ---
def init_db():
    conn = sqlite3.connect("web_sales_dialer.db")
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS leads
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       name
                       TEXT,
                       phone
                       TEXT,
                       program
                       TEXT,
                       status
                       TEXT,
                       notes
                       TEXT,
                       last_called
                       TEXT,
                       next_call
                       TEXT
                   )
                   ''')

    cursor.execute("PRAGMA table_info(leads)")
    columns = [col[1] for col in cursor.fetchall()]
    if "next_call" not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN next_call TEXT")

    # ტესტური მონაცემები ამოღებულია სუფთა სტარტისთვის
    conn.close()


init_db()

# --- ULTRA MODERN PRO UI HTML/JS/CSS TEMPLATE ---
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ka" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Sales Dialer Pro v3.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: { sans: ['Plus Jakarta Sans', 'sans-serif'] },
                    colors: {
                        darkbg: '#090D16',
                        cardbg: '#111827',
                        accent: { 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca' }
                    }
                }
            }
        }
    </script>
    <style>
        .glass-panel {
            background: rgba(17, 24, 39, 0.85);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .active-card {
            border-color: #6366f1 !important;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
            background: rgba(30, 41, 59, 0.95) !important;
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    </style>
</head>
<body class="bg-darkbg text-slate-100 h-screen flex flex-col font-sans overflow-hidden antialiased">

    <!-- Top Navigation Header -->
    <header class="glass-panel px-6 py-3 flex justify-between items-center z-10 shadow-lg">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <span class="text-xl">⚡</span>
            </div>
            <div>
                <h1 class="text-lg font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
                    Smart Dialer <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 font-semibold ml-1">PRO v3.0</span>
                </h1>
                <p class="text-[11px] text-slate-400">გაყიდვების ავტომატიზებული პორტალი</p>
            </div>
        </div>

        <!-- Real-Time KPI Stats Bar -->
        <div class="hidden lg:flex items-center space-x-6 bg-slate-900/90 px-6 py-2 rounded-xl border border-slate-800">
            <div class="text-center">
                <span class="text-[10px] uppercase tracking-wider text-slate-400 font-bold">სულ ბაზა</span>
                <p id="statTotal" class="text-lg font-black text-white">0</p>
            </div>
            <div class="h-6 w-px bg-slate-800"></div>
            <div class="text-center">
                <span class="text-[10px] uppercase tracking-wider text-amber-400 font-bold">დასარეკი</span>
                <p id="statPending" class="text-lg font-black text-amber-400">0</p>
            </div>
            <div class="h-6 w-px bg-slate-800"></div>
            <div class="text-center">
                <span class="text-[10px] uppercase tracking-wider text-emerald-400 font-bold">დაინტერესდა</span>
                <p id="statSuccess" class="text-lg font-black text-emerald-400">0</p>
            </div>
            <div class="h-6 w-px bg-slate-800"></div>
            <div class="text-center">
                <span class="text-[10px] uppercase tracking-wider text-sky-400 font-bold">გადარეკვა</span>
                <p id="statCallback" class="text-lg font-black text-sky-400">0</p>
            </div>
        </div>

        <!-- Controls -->
        <div class="flex items-center space-x-2">
            <!-- 📄 შაბლონის ჩამოტვირთვის ღილაკი -->
            <a href="/api/download_template" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-700 transition flex items-center space-x-1.5">
                <span>📄 შაბლონი</span>
            </a>
            <a href="/api/export_csv" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-700 transition flex items-center space-x-1.5">
                <span>📤 ექსპორტი</span>
            </a>
            <label class="cursor-pointer bg-indigo-900/40 hover:bg-indigo-900/60 text-indigo-300 px-3 py-1.5 rounded-xl text-xs font-semibold border border-indigo-700/50 transition flex items-center space-x-1.5">
                <span>📥 იმპორტი</span>
                <input type="file" id="csvFileInput" accept=".csv" class="hidden" onchange="uploadCSV()">
            </label>
            <div class="flex items-center space-x-2 bg-slate-900/90 px-3 py-1.5 rounded-xl border border-slate-800">
                <span class="text-xs text-slate-300 font-semibold">🚀 Auto-Dial</span>
                <input type="checkbox" id="autoDialToggle" class="w-4 h-4 text-indigo-600 bg-slate-900 border-slate-700 rounded focus:ring-0">
            </div>
        </div>
    </header>

    <!-- Main Content Workspace -->
    <main class="flex-1 grid grid-cols-12 gap-4 p-4 overflow-hidden">

        <!-- Left: Directory Panel (3 Cols) -->
        <section class="col-span-12 md:col-span-4 lg:col-span-3 glass-panel rounded-2xl flex flex-col overflow-hidden shadow-xl">
            <div class="p-4 border-b border-slate-800/80 space-y-3">
                <input type="text" id="searchInput" onkeyup="filterLeads()" placeholder="🔍 ძებნა სახელით ან ნომრით..." 
                       class="w-full bg-slate-900/90 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition">
                <div class="grid grid-cols-3 gap-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800/80">
                    <button onclick="setFilter('ყველა')" class="filter-btn py-1.5 text-[11px] font-bold rounded-lg bg-indigo-600 text-white transition shadow" id="filter-all">ყველა</button>
                    <button onclick="setFilter('🟡 დასარეკია')" class="filter-btn py-1.5 text-[11px] font-bold rounded-lg text-slate-400 hover:text-slate-200 transition" id="filter-pending">დასარეკი</button>
                    <button onclick="setFilter('🟠 გადარეკვა')" class="filter-btn py-1.5 text-[11px] font-bold rounded-lg text-slate-400 hover:text-slate-200 transition" id="filter-callback">გადარეკვა</button>
                </div>
            </div>
            <div id="leadList" class="flex-1 overflow-y-auto p-3 space-y-2">
                <!-- Dynamic Lead Cards -->
            </div>
        </section>

        <!-- Center: Active Call Command Center (6 Cols) -->
        <section class="col-span-12 md:col-span-8 lg:col-span-6 glass-panel rounded-2xl flex flex-col p-6 overflow-y-auto justify-between space-y-4 shadow-xl">

            <!-- Banner Header with Nav -->
            <div class="flex justify-between items-start bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                <div class="flex-1">
                    <div class="flex items-center space-x-2">
                        <span id="activeStatusBadge" class="text-[10px] px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 font-bold border border-slate-700">აირჩიეთ კლიენტი</span>
                        <span id="activeProgram" class="text-xs text-indigo-400 font-semibold"></span>
                    </div>
                    <h2 id="activeName" class="text-2xl font-extrabold text-white mt-1">კლიენტი არ არის არჩეული</h2>
                    <div class="flex items-center space-x-3 mt-1">
                        <p id="activePhone" class="text-sm font-mono text-slate-300 font-bold">+995 5XX XX XX XX</p>
                        <span id="activeNextCall" class="hidden text-[11px] bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-md font-medium"></span>
                    </div>
                </div>

                <div class="flex flex-col items-end space-y-2">
                    <div class="flex items-center space-x-2">
                        <span id="livePulse" class="w-3 h-3 rounded-full bg-slate-600"></span>
                        <div id="callTimer" class="text-3xl font-mono font-black text-indigo-400">00:00</div>
                    </div>
                    <!-- Prev / Next Lead Nav -->
                    <div class="flex space-x-1">
                        <button onclick="navLead(-1)" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg text-xs font-bold border border-slate-700">◀ წინა</button>
                        <button onclick="navLead(1)" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg text-xs font-bold border border-slate-700">შემდეგი ▶</button>
                    </div>
                </div>
            </div>

            <!-- Call & Communication Trigger Bar -->
            <div class="grid grid-cols-12 gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
                <a id="callButton" href="#" onclick="triggerCall(event)" 
                   class="col-span-8 bg-slate-800 text-slate-500 cursor-not-allowed font-extrabold px-6 py-3.5 rounded-xl transition shadow-lg flex items-center justify-center space-x-2 text-sm pointer-events-none">
                    <span class="text-lg">📞</span>
                    <span>დარეკვა (Headset)</span>
                </a>

                <a id="whatsappButton" href="#" target="_blank" onclick="triggerWA(event)"
                   class="col-span-4 bg-slate-800 text-slate-500 cursor-not-allowed font-bold px-4 py-3.5 rounded-xl transition flex items-center justify-center space-x-2 text-xs pointer-events-none border border-slate-700">
                    <span class="text-base">💬</span>
                    <span>WhatsApp</span>
                </a>
            </div>

            <!-- Live Notes & Quick Tags -->
            <div class="flex-1 flex flex-col space-y-2">
                <div class="flex justify-between items-center">
                    <div class="flex items-center space-x-2">
                        <label class="text-xs font-bold uppercase tracking-wider text-slate-300">📝 საუბრის შენიშვნა</label>
                        <span id="saveIndicator" class="text-[10px] text-emerald-400 font-semibold opacity-0 transition">✓ შენახულია</span>
                    </div>
                    <div class="flex flex-wrap gap-1">
                        <button onclick="addTag('💰 განვადება სურს')" class="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded-md border border-slate-700 transition">+ 💰 განვადება</button>
                        <button onclick="addTag('⏳ დრო სჭირდება')" class="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded-md border border-slate-700 transition">+ ⏳ დრო</button>
                        <button onclick="addTag('📧 ინფო გაეგზავნა')" class="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded-md border border-slate-700 transition">+ 📧 ინფო</button>
                        <button onclick="addTag('❌ ძვირია')" class="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded-md border border-slate-700 transition">+ ❌ ძვირია</button>
                    </div>
                </div>
                <textarea id="activeNotes" oninput="onNotesInput()" placeholder="ჩაწერეთ დეტალები ან გამოიყენეთ სწრაფი ტეგები..." 
                          class="flex-1 w-full bg-slate-900/90 border border-slate-800 rounded-xl p-4 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 resize-none min-h-[140px] transition"></textarea>
            </div>
        </section>

        <!-- Right: One-Touch Dispositions (3 Cols) -->
        <section class="col-span-12 lg:col-span-3 glass-panel rounded-2xl p-5 flex flex-col justify-between space-y-4 shadow-xl">
            <div>
                <h3 class="text-xs font-extrabold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 mb-4">
                    ⚡ 1-კლიკიანი შედეგი
                </h3>

                <div class="space-y-2.5">
                    <button onclick="setDisposition('🟢 დაინტერესდა')" 
                            class="w-full bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 font-bold py-3 px-4 rounded-xl text-left transition flex justify-between items-center group shadow-sm">
                        <span class="text-xs">🟢 ჩაეწერა / დაინტერესდა</span>
                        <span class="opacity-0 group-hover:opacity-100 transition text-sm">➔</span>
                    </button>
                    <button onclick="openCallbackModal()" 
                            class="w-full bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 font-bold py-3 px-4 rounded-xl text-left transition flex justify-between items-center group shadow-sm">
                        <span class="text-xs">🟠 გადარეკვა (Callback)</span>
                        <span class="opacity-0 group-hover:opacity-100 transition text-sm">📅</span>
                    </button>
                    <button onclick="setDisposition('⚪ არ უპასუხა')" 
                            class="w-full bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 text-sky-300 font-bold py-3 px-4 rounded-xl text-left transition flex justify-between items-center group shadow-sm">
                        <span class="text-xs">⚪ არ უპასუხა (No Answer)</span>
                        <span class="opacity-0 group-hover:opacity-100 transition text-sm">➔</span>
                    </button>
                    <button onclick="setDisposition('🔴 უარი')" 
                            class="w-full bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 font-bold py-3 px-4 rounded-xl text-left transition flex justify-between items-center group shadow-sm">
                        <span class="text-xs">🔴 უარი / უარყოფა</span>
                        <span class="opacity-0 group-hover:opacity-100 transition text-sm">➔</span>
                    </button>
                </div>
            </div>

            <div class="bg-slate-900/90 border border-slate-800 p-3 rounded-xl text-center">
                <p class="text-[11px] text-slate-400">Headset Audio Status</p>
                <span class="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-bold mt-0.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span> Live Connected
                </span>
            </div>
        </section>

    </main>

    <!-- Callback Date/Time Modal -->
    <div id="callbackModal" class="hidden fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-4">
            <h3 class="text-base font-bold text-white flex items-center gap-2">📅 გადარეკვის დროის დანიშნვა</h3>
            <p class="text-xs text-slate-400">აირჩიეთ სწრაფი ინტერვალი ან მონიშნეთ თარიღი/დრო:</p>

            <div class="grid grid-cols-2 gap-2">
                <button onclick="setPresetCallback(1)" class="bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-xl text-xs font-semibold border border-slate-700">+1 საათში</button>
                <button onclick="setPresetCallback(3)" class="bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-xl text-xs font-semibold border border-slate-700">+3 საათში</button>
                <button onclick="setPresetCallback(24)" class="bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-xl text-xs font-semibold border border-slate-700">ხვალ ამ დროს</button>
                <button onclick="setPresetCallback(48)" class="bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-xl text-xs font-semibold border border-slate-700">2 დღეში</button>
            </div>

            <div class="pt-2">
                <label class="text-xs font-semibold text-slate-300">მორგებული თარიღი & დრო:</label>
                <input type="datetime-local" id="customCallbackInput" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white mt-1 focus:outline-none focus:border-indigo-500">
            </div>

            <div class="flex justify-end space-x-2 pt-2">
                <button onclick="closeCallbackModal()" class="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700">გაუქმება</button>
                <button onclick="confirmCallbackModal()" class="px-5 py-2 rounded-xl text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-lg">შენახვა</button>
            </div>
        </div>
    </div>

    <!-- Client-side Logic -->
    <script>
        let currentLead = null;
        let leadsData = [];
        let activeFilter = 'ყველა';
        let timerInterval = null;
        let timerSeconds = 0;
        let saveTimeout = null;

        async function fetchLeads() {
            const res = await fetch('/api/leads');
            leadsData = await res.json();
            updateKPIs();
            renderLeads();
        }

        function updateKPIs() {
            document.getElementById('statTotal').innerText = leadsData.length;
            document.getElementById('statPending').innerText = leadsData.filter(l => l.status === '🟡 დასარეკია').length;
            document.getElementById('statSuccess').innerText = leadsData.filter(l => l.status === '🟢 დაინტერესდა').length;
            document.getElementById('statCallback').innerText = leadsData.filter(l => l.status === '🟠 გადარეკვა').length;
        }

        function renderLeads() {
            const listEl = document.getElementById('leadList');
            const search = document.getElementById('searchInput').value.toLowerCase();
            listEl.innerHTML = '';

            const filtered = leadsData.filter(l => {
                const matchesSearch = l.name.toLowerCase().includes(search) || l.phone.includes(search);
                const matchesFilter = activeFilter === 'ყველა' ? true : l.status === activeFilter;
                return matchesSearch && matchesFilter;
            });

            filtered.forEach(lead => {
                const isSelected = currentLead && currentLead.id === lead.id;
                const card = document.createElement('div');
                card.className = `p-3.5 rounded-xl border cursor-pointer transition ${isSelected ? 'active-card' : 'bg-slate-900/60 border-slate-800/90 hover:border-slate-700 hover:bg-slate-900/90'}`;
                card.onclick = () => selectLead(lead);
                card.innerHTML = `
                    <div class="flex justify-between items-start">
                        <h4 class="font-bold text-xs text-slate-100">${lead.name}</h4>
                        <span class="text-[9px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-200 font-bold border border-slate-700">${lead.status}</span>
                    </div>
                    <div class="text-[11px] font-mono text-slate-300 font-medium mt-1">${lead.phone}</div>
                    <div class="flex justify-between items-center mt-1">
                        <span class="text-[10px] text-indigo-400 font-semibold">${lead.program || 'ზოგადი'}</span>
                        ${lead.next_call ? `<span class="text-[9px] text-amber-400 font-medium">📅 ${lead.next_call}</span>` : ''}
                    </div>
                `;
                listEl.appendChild(card);
            });
        }

        function selectLead(lead) {
            currentLead = lead;
            document.getElementById('activeName').innerText = lead.name;
            document.getElementById('activePhone').innerText = lead.phone;
            document.getElementById('activeProgram').innerText = lead.program || 'ზოგადი';
            document.getElementById('activeStatusBadge').innerText = lead.status;
            document.getElementById('activeNotes').value = lead.notes || '';

            const nextCallEl = document.getElementById('activeNextCall');
            if (lead.next_call) {
                nextCallEl.innerText = '📅 გადარეკვა: ' + lead.next_call;
                nextCallEl.classList.remove('hidden');
            } else {
                nextCallEl.classList.add('hidden');
            }

            // Enable Call & WhatsApp Buttons
            const callBtn = document.getElementById('callButton');
            callBtn.href = `tel:${lead.phone}`;
            callBtn.className = "col-span-8 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-extrabold px-6 py-3.5 rounded-xl transition shadow-lg shadow-emerald-600/30 flex items-center justify-center space-x-2 text-sm cursor-pointer";

            const waBtn = document.getElementById('whatsappButton');
            const cleanPhone = lead.phone.replace(/[^0-9]/g, '');
            const waMsg = encodeURIComponent(`გამარჯობა ${lead.name}, გიკავშირდებით Skillwill-იდან კურსთან (${lead.program}) დაკავშირებით.`);
            waBtn.href = `https://wa.me/${cleanPhone}?text=${waMsg}`;
            waBtn.className = "col-span-4 bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 font-bold px-4 py-3.5 rounded-xl transition flex items-center justify-center space-x-2 text-xs cursor-pointer border border-emerald-500/40 shadow-sm";

            renderLeads();
        }

        function navLead(dir) {
            if (!leadsData.length) return;
            if (!currentLead) {
                selectLead(leadsData[0]);
                return;
            }
            const idx = leadsData.findIndex(l => l.id === currentLead.id);
            if (idx !== -1) {
                const nextIdx = (idx + dir + leadsData.length) % leadsData.length;
                selectLead(leadsData[nextIdx]);
            }
        }

        function triggerCall(e) {
            if (!currentLead) {
                e.preventDefault();
                return;
            }
            startTimer();
        }

        function triggerWA(e) {
            if (!currentLead) e.preventDefault();
        }

        function startTimer() {
            stopTimer();
            timerSeconds = 0;
            document.getElementById('livePulse').className = 'w-3 h-3 rounded-full bg-emerald-500 animate-ping';

            timerInterval = setInterval(() => {
                timerSeconds++;
                const mins = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
                const secs = String(timerSeconds % 60).padStart(2, '0');
                document.getElementById('callTimer').innerText = `${mins}:${secs}`;
            }, 1000);
        }

        function stopTimer() {
            if (timerInterval) clearInterval(timerInterval);
            document.getElementById('callTimer').innerText = "00:00";
            document.getElementById('livePulse').className = 'w-3 h-3 rounded-full bg-slate-600';
        }

        function onNotesInput() {
            const ind = document.getElementById('saveIndicator');
            ind.innerText = 'ინახება...';
            ind.classList.remove('opacity-0');
            if (saveTimeout) clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => {
                ind.innerText = '✓ შენახულია';
                setTimeout(() => ind.classList.add('opacity-0'), 1500);
            }, 800);
        }

        function addTag(tagText) {
            const notesEl = document.getElementById('activeNotes');
            notesEl.value = notesEl.value.trim() === '' ? tagText : notesEl.value + ' | ' + tagText;
            onNotesInput();
        }

        // Callback Modal Handlers
        function openCallbackModal() {
            if (!currentLead) {
                alert('აირჩიეთ კლიენტი!');
                return;
            }
            document.getElementById('callbackModal').classList.remove('hidden');
        }

        function closeCallbackModal() {
            document.getElementById('callbackModal').classList.add('hidden');
        }

        function setPresetCallback(hours) {
            const now = new Date();
            now.setHours(now.getHours() + hours);
            const str = now.toISOString().slice(0,16).replace('T', ' ');
            saveDispositionWithCallback('🟠 გადარეკვა', str);
            closeCallbackModal();
        }

        function confirmCallbackModal() {
            const val = document.getElementById('customCallbackInput').value;
            const formatted = val ? val.replace('T', ' ') : '';
            saveDispositionWithCallback('🟠 გადარეკვა', formatted);
            closeCallbackModal();
        }

        async function saveDispositionWithCallback(status, nextCallTime) {
            stopTimer();
            const notes = document.getElementById('activeNotes').value;

            await fetch('/api/disposition', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: currentLead.id, status, notes, next_call: nextCallTime })
            });

            await fetchLeads();
            checkAutoDial();
        }

        async function setDisposition(status) {
            if (!currentLead) {
                alert('აირჩიეთ კლიენტი!');
                return;
            }
            saveDispositionWithCallback(status, '');
        }

        function checkAutoDial() {
            if (document.getElementById('autoDialToggle').checked) {
                const nextLead = leadsData.find(l => l.status === '🟡 დასარეკია');
                if (nextLead) {
                    selectLead(nextLead);
                    setTimeout(() => {
                        window.location.href = `tel:${nextLead.phone}`;
                        startTimer();
                    }, 1200);
                } else {
                    alert('ყველა დასარეკი კლიენტი დამუშავებულია!');
                }
            }
        }

        function setFilter(filter) {
            activeFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(b => {
                b.classList.remove('bg-indigo-600', 'text-white', 'shadow');
                b.classList.add('text-slate-400');
            });
            renderLeads();
        }

        function filterLeads() { renderLeads(); }

        async function uploadCSV() {
            const input = document.getElementById('csvFileInput');
            if (!input.files[0]) return;

            const formData = new FormData();
            formData.append('file', input.files[0]);

            const res = await fetch('/api/upload_csv', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.success) {
                alert(`წარმატებით აიტვირთა ${data.count} ახალი კონტაქტი!`);
                fetchLeads();
            } else {
                alert('შეცდომა ატვირთვისას!');
            }
        }

        fetchLeads();
    </script>
</body>
</html>"""


# --- API MARSHRUTEBI ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/leads', methods=['GET'])
def get_leads():
    conn = sqlite3.connect("web_sales_dialer.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, program, status, notes, last_called, next_call FROM leads ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    leads = [
        {"id": r[0], "name": r[1], "phone": r[2], "program": r[3], "status": r[4], "notes": r[5], "last_called": r[6],
         "next_call": r[7]}
        for r in rows
    ]
    return jsonify(leads)


@app.route('/api/disposition', methods=['POST'])
def save_disposition():
    data = request.json
    lead_id = data.get('id')
    status = data.get('status')
    notes = data.get('notes')
    next_call = data.get('next_call', '')
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect("web_sales_dialer.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ?, notes = ?, last_called = ?, next_call = ? WHERE id = ?",
                   (status, notes, now, next_call, lead_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route('/api/upload_csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files['file']
    stream = io.StringIO(file.stream.read().decode("UTF-8-SIG"), newline=None)
    reader = csv.reader(stream)
    header = next(reader, None)

    count = 0
    conn = sqlite3.connect("web_sales_dialer.db")
    cursor = conn.cursor()

    for row in reader:
        if row and len(row) >= 2:
            name, phone = row[0].strip(), row[1].strip()
            program = row[2].strip() if len(row) > 2 else "ზოგადი"
            notes = row[3].strip() if len(row) > 3 else ""
            if name and phone:
                cursor.execute(
                    "INSERT INTO leads (name, phone, program, status, notes, last_called, next_call) VALUES (?, ?, ?, '🟡 დასარეკია', ?, '', '')",
                    (name, phone, program, notes)
                )
                count += 1

    conn.commit()
    conn.close()
    return jsonify({"success": True, "count": count})


@app.route('/api/export_csv', methods=['GET'])
def export_csv():
    conn = sqlite3.connect("web_sales_dialer.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, program, status, notes, last_called, next_call FROM leads ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["სახელი გვარი", "ტელეფონი", "პროგრამა", "სტატუსი", "შენიშვნები", "ბოლო ზარი", "გადარეკვის დრო"])
    writer.writerows(rows)

    response = Response(output.getvalue().encode('utf-8-sig'), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=sales_leads_export.csv"
    return response


# 📄 მზა CSV შაბლონის ჩამოტვირთვის მარშრუტი
@app.route('/api/download_template', methods=['GET'])
def download_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["სახელი გვარი", "ტელეფონი", "პროგრამა", "შენიშვნა"])
    writer.writerow(["გიორგი ბერიძე", "+995599112233", "Full-stack Python", "დაინტერესებულია ვებ-დეველოპმენტით"])
    writer.writerow(["ნინო კაპანაძე", "+995577445566", "UI/UX Design", "სურს განვადების პირობების გაგება"])

    response = Response(output.getvalue().encode('utf-8-sig'), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=sales_leads_template.csv"
    return response


if __name__ == '__main__':
    print("🚀 Web Dialer PRO v3.0 გაშვეულია! გახსენი ბრაუზერში: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)