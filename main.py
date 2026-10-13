import tkinter as tk
from tkinter import messagebox
import csv
import os
import struct
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pymodbus.client import ModbusSerialClient

# ==========================================
# TEMA HMI MODERN FLAT (Bersih & Profesional)
# ==========================================
BG_MAIN = "#E2E8F0"
BG_PANEL = "#FFFFFF"
BG_TITLE = "#1E293B"
BG_HEADER2 = "#334155"
BORDER = "#CBD5E1"
BG_VALUE = "#F1F5F9"
TEXT = "#0F172A"
TEXT_MUTED = "#64748B"
OK = "#10B981"
DANGER = "#EF4444"
INFO = "#3B82F6"
LINE_COLORS = ["#3B82F6", "#EF4444", "#10B981", "#8B5CF6"]

F_TITLE = ("Segoe UI", 9, "bold")
F_LABEL = ("Segoe UI", 9)
F_VALUE = ("Consolas", 10, "bold")

# ==========================================
# KONFIGURASI MODBUS
# ==========================================
modbus_client = ModbusSerialClient(
    port='/dev/ttyUSB0',
    baudrate=9600,
    timeout=0.5,
    bytesize=8,
    parity='N',
    stopbits=1,
)

SLAVE_TEMP = 1   # ID modul Suhu
SLAVE_IN   = 2   # ID PM220 (Input)
SLAVE_OUT  = 3   # ID PM220 (Output)

def konversi_ke_float(res):
    if res.isError() or len(res.registers) < 2:
        return 0.0
    packed_bytes = struct.pack('>HH', res.registers[0], res.registers[1])
    return round(struct.unpack('>f', packed_bytes)[0], 2)

def konversi_ke_int64(res):
    if res.isError() or len(res.registers) < 4:
        return 0
    packed_bytes = struct.pack('>HHHH', res.registers[0], res.registers[1], res.registers[2], res.registers[3])
    return struct.unpack('>q', packed_bytes)[0]

# ==========================================
# FUNGSI GUI
# ==========================================
def panel(parent, title, btn_text=None):
    outer = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
    bar = tk.Frame(outer, bg=BG_HEADER2)
    bar.pack(fill="x")
    tk.Label(bar, text=title, bg=BG_HEADER2, fg="white", font=F_TITLE, pady=4).pack(side="left", padx=8)
    if btn_text:
        tk.Button(bar, text=btn_text, font=("Segoe UI", 7, "bold"), relief="flat", bd=0,
                  bg="#475569", fg="white", activebackground="#64748B", activeforeground="white", 
                  padx=8, pady=2, cursor="hand2").pack(side="right", padx=6, pady=2)
    body = tk.Frame(outer, bg=BG_PANEL)
    body.pack(fill="both", expand=True, padx=8, pady=8)
    return outer, body

def value_box(parent, text_var, width=11):
    frame = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    lbl = tk.Label(frame, textvariable=text_var, width=width, anchor="e", bg=BG_VALUE, fg=TEXT,
                   font=F_VALUE, padx=6, pady=2)
    lbl.pack(fill="both", expand=True)
    return frame

def chart_panel(parent, title, lines, readouts_vars, btn_text, ylim):
    outer, body = panel(parent, title, btn_text)

    fig = Figure(figsize=(4, 1.9), dpi=90)
    fig.patch.set_facecolor(BG_PANEL)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.18)
    
    ax = fig.add_subplot(111)
    line_objs = []
    for i, name in enumerate(lines):
        line, = ax.plot([], [], label=name, color=LINE_COLORS[i % 4], linewidth=2.0)
        line_objs.append(line)
        
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=len(lines), frameon=False, fontsize=8)
    ax.tick_params(labelsize=8, colors=TEXT_MUTED)
    ax.grid(True, linestyle="--", alpha=0.4, color=TEXT_MUTED)
    ax.set_ylim(*ylim)
    
    for s in ax.spines.values():
        s.set_color(BORDER)

    cv = FigureCanvasTkAgg(fig, master=body)
    cv.get_tk_widget().pack(fill="both", expand=True, pady=(0, 4))

    row = tk.Frame(body, bg=BG_PANEL)
    row.pack(fill="x")
    for i, (lbl, var) in enumerate(readouts_vars):
        cell = tk.Frame(row, bg=BG_PANEL)
        cell.pack(side="left", expand=True, fill="x", padx=2)
        tk.Label(cell, text="■", fg=LINE_COLORS[i % 4], bg=BG_PANEL, font=("Segoe UI", 10)).pack(side="left")
        tk.Label(cell, text=lbl, bg=BG_PANEL, fg=TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=2)
        value_box(cell, var, width=9).pack(side="right")
        
    return outer, line_objs, cv

def param_panel(parent, ui_vars):
    outer, body = panel(parent, "PARAMETER LISTRIK")
    groups = [
        ("Daya", [("Reactive Power In", ui_vars["kvar_in"]), ("Reactive Power Out", ui_vars["kvar_out"]),
                  ("Apparent Power In", ui_vars["kva_in"]), ("Apparent Power Out", ui_vars["kva_out"])]),
        ("Energi", [("Energy In Delivered", ui_vars["wh_in"]), ("Energy Out Received", ui_vars["wh_out"])]),
        ("Harmonik", [("Harmonic Current", ui_vars["harm_c"]), ("Harmonic Voltage", ui_vars["harm_v"])]),
        ("Kinerja", [("Frekuensi IN", ui_vars["freq"]), ("Power Factor IN", ui_vars["pf"])]),
    ]
    r = 0
    for name, items in groups:
        tk.Label(body, text=name.upper(), bg=BG_PANEL, fg=LINE_COLORS[0], font=("Segoe UI", 8, "bold"),
                 anchor="w").grid(row=r, column=0, columnspan=2, sticky="w", pady=(8 if r>0 else 0, 2))
        tk.Frame(body, bg=BORDER, height=1).grid(row=r + 1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        r += 2
        for lbl, var in items:
            tk.Label(body, text=lbl, bg=BG_PANEL, fg=TEXT, font=F_LABEL, anchor="w").grid(row=r, column=0, sticky="w", pady=2)
            value_box(body, var, width=12).grid(row=r, column=1, sticky="e", pady=2, padx=(8, 0))
            r += 1
    body.columnconfigure(0, weight=1)
    return outer

def status_panel(parent, on_manual_save, on_clear_charts):
    outer, body = panel(parent, "STATUS & KONTROL")
    top_layout = tk.Frame(body, bg=BG_PANEL)
    top_layout.pack(fill="x")

    left = tk.Frame(top_layout, bg=BG_PANEL)
    left.pack(side="left", padx=(4, 16))
    tk.Label(left, text="LN₂ Level", bg=BG_PANEL, fg=TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(pady=(0, 4))
    
    # PERBAIKAN SINTAKS CANVAS ERROR DI SINI
    tank = tk.Canvas(left, width=44, height=100, bg=BG_VALUE, highlightbackground=BORDER, highlightthickness=1)
    tank.pack(pady=4)
    level = 0
    fill_h = int(96 * level / 100)
    tank.create_rectangle(2, 98 - fill_h, 44, 98, fill=INFO, outline="")
    for p in (0, 50, 100):
        y = 98 - int(96 * p / 100)
        tank.create_line(0, y, 8, y, fill=TEXT_MUTED)
        
    dummy_var = tk.StringVar(value=f"{level} %")
    value_box(left, dummy_var, width=6).pack(pady=(4, 0))

    right = tk.Frame(top_layout, bg=BG_PANEL)
    right.pack(side="left", fill="both", expand=True)
    tk.Label(right, text="KONTROL AKSI", bg=BG_PANEL, fg=LINE_COLORS[0], font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 10))
    
    tk.Button(right, text="Ekspor Data ke CSV", font=("Segoe UI", 8, "bold"), 
              bg=OK, fg="white", activebackground="#059669", activeforeground="white",
              relief="flat", bd=0, padx=8, pady=8, cursor="hand2",
              command=on_manual_save).pack(fill="x", pady=4)

    tk.Button(right, text="Clear All Chart", font=("Segoe UI", 8, "bold"), 
              bg=DANGER, fg="white", activebackground="#DC2626", activeforeground="white",
              relief="flat", bd=0, padx=8, pady=8, cursor="hand2",
              command=on_clear_charts).pack(fill="x", pady=4)

    return outer

def build_gui():
    root = tk.Tk()
    root.title("Sistem Monitoring Trafo Superkonduktor")
    
    # === SETTING FULLSCREEN ===
    root.attributes('-fullscreen', True)
    root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False)) # Tekan ESC untuk keluar fullscreen
    root.configure(bg=BG_MAIN)
    
    all_chart_refs = []
    collected_data = [] # List untuk menyimpan semua baris data tiap 1 detik
    
    # ----------------------------------------------------
    # INISIALISASI VARIABEL DINAMIS UNTUK GUI
    # ----------------------------------------------------
    ui_vars = {
        "t1": tk.StringVar(value="0.0 °C"), "t2": tk.StringVar(value="0.0 °C"),
        "t3": tk.StringVar(value="0.0 °C"), "t4": tk.StringVar(value="0.0 °C"),
        "v_in": tk.StringVar(value="0.0 V"), "v_out": tk.StringVar(value="0.0 V"),
        "c_in": tk.StringVar(value="0.0 A"), "c_out": tk.StringVar(value="0.0 A"),
        "p_in": tk.StringVar(value="0.0 kW"), "p_out": tk.StringVar(value="0.0 kW"),
        "kvar_in": tk.StringVar(value="0.0 kVAR"), "kvar_out": tk.StringVar(value="0.0 kVAR"),
        "kva_in": tk.StringVar(value="0.0 kVA"), "kva_out": tk.StringVar(value="0.0 kVA"),
        "wh_in": tk.StringVar(value="0 Wh"), "wh_out": tk.StringVar(value="0 Wh"),
        "harm_c": tk.StringVar(value="0.0 %"), "harm_v": tk.StringVar(value="0.0 %"),
        "freq": tk.StringVar(value="0.0 Hz"), "pf": tk.StringVar(value="0.0")
    }

    # Data Historis untuk Grafik
    hist_data = { "t1": [], "t2": [], "t3": [], "t4": [], "v_in": [], "v_out": [], "c_in": [], "c_out": [], "p_in": [], "p_out": [] }
    waktu_x = []

    # ---------- Title bar ----------
    top = tk.Frame(root, bg=BG_TITLE, height=45)
    top.pack(fill="x")
    top.pack_propagate(False)
    
    tk.Label(top, text="SISTEM MONITORING", bg=BG_TITLE, fg="#94A3B8", font=("Segoe UI", 11)).pack(side="left", padx=(16, 4), pady=10)
    tk.Label(top, text="TRAFO SUPERKONDUKTOR", bg=BG_TITLE, fg="white", font=("Segoe UI", 11, "bold")).pack(side="left", pady=10)
    clock = tk.Label(top, bg=BG_TITLE, fg="#94A3B8", font=("Consolas", 10, "bold"))
    clock.pack(side="right", padx=16, pady=10)

    # ---------- Status bar (bawah) ----------
    status = tk.Frame(root, bg="#FFFFFF", highlightbackground=BORDER, highlightthickness=1)
    status.pack(side="bottom", fill="x")
    
    tk.Label(status, text="●", fg=OK, bg="#FFFFFF", font=("Segoe UI", 10)).pack(side="left", padx=(12, 4), pady=4)
    status_msg = tk.Label(status, text="Sistem Beroperasi Normal", bg="#FFFFFF", fg=TEXT, font=("Segoe UI", 9, "bold"))
    status_msg.pack(side="left", pady=4)
    
    save_lbl = tk.Label(status, text="AUTO-COLLECT: AKTIF (Tiap 1s)", bg="#FFFFFF", fg=INFO, font=("Segoe UI", 8, "bold"))
    save_lbl.pack(side="right", padx=16, pady=4)

    def flash_status(message, color):
        old_text = status_msg.cget("text")
        old_color = status_msg.cget("fg")
        status_msg.config(text=message, fg=color)
        root.after(3000, lambda: status_msg.config(text=old_text, fg=old_color))

    # EKSPOR SEMUA DATA YANG TERKUMPUL KE CSV
    def manual_save_action():
        if not collected_data:
            messagebox.showwarning("Peringatan", "Belum ada data yang terkumpul untuk diekspor!")
            return
            
        # PERBAIKAN: Memaksa file tersimpan di lokasi script Python ini berada
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = f"datalog_trafo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = os.path.join(script_dir, filename)
        
        try:
            with open(file_path, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=collected_data[0].keys())
                writer.writeheader()
                writer.writerows(collected_data)
            
            # Pop-up Sukses sekarang menampilkan path lengkap file
            messagebox.showinfo("Simpan Berhasil", f"Berhasil mengekspor {len(collected_data)} baris data ke:\n\n{file_path}")
            flash_status("Data Berhasil Diekspor!", INFO)
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan ke CSV:\n{e}")

    def clear_charts_action():
        waktu_x.clear()
        collected_data.clear() 
        for key in hist_data:
            hist_data[key].clear()
        for lines, canvas in all_chart_refs:
            for line in lines:
                line.set_data([], [])
            canvas.draw()
        flash_status("Berhasil: Semua Grafik & Data Kosong!", DANGER)

    def update_grafik():
        if len(waktu_x) > 60: 
            waktu_x.pop(0)
            for key in hist_data: hist_data[key].pop(0)
            
        all_chart_refs[0][0][0].set_data(range(len(waktu_x)), hist_data["t1"])
        all_chart_refs[0][0][1].set_data(range(len(waktu_x)), hist_data["t2"])
        all_chart_refs[0][0][2].set_data(range(len(waktu_x)), hist_data["t3"])
        all_chart_refs[0][0][3].set_data(range(len(waktu_x)), hist_data["t4"])
        all_chart_refs[0][1].draw()

        all_chart_refs[1][0][0].set_data(range(len(waktu_x)), hist_data["p_in"])
        all_chart_refs[1][0][1].set_data(range(len(waktu_x)), hist_data["p_out"])
        all_chart_refs[1][1].draw()
        
        all_chart_refs[2][0][0].set_data(range(len(waktu_x)), hist_data["v_in"])
        all_chart_refs[2][0][1].set_data(range(len(waktu_x)), hist_data["v_out"])
        all_chart_refs[2][1].draw()

        all_chart_refs[3][0][0].set_data(range(len(waktu_x)), hist_data["c_in"])
        all_chart_refs[3][0][1].set_data(range(len(waktu_x)), hist_data["c_out"])
        all_chart_refs[3][1].draw()
        
        for lines, ax_canvas in all_chart_refs:
            ax = lines[0].axes
            ax.set_xlim(0, max(60, len(waktu_x)))

    # LOOP PEMBACAAN DATA (Tiap 1 Detik)
    def tick():
        clock.config(text=datetime.now().strftime("%d-%m-%Y  %H:%M:%S"))
        
        if modbus_client.connect():
            # --- BACA SUHU (SLAVE 1) ---
            t1 = modbus_client.read_input_registers(address=1000, count=1, slave=SLAVE_TEMP)
            t2 = modbus_client.read_input_registers(address=1006, count=1, slave=SLAVE_TEMP)
            t3 = modbus_client.read_input_registers(address=1012, count=1, slave=SLAVE_TEMP)
            t4 = modbus_client.read_input_registers(address=1018, count=1, slave=SLAVE_TEMP)
            
            val_t1 = t1.registers[0] if not t1.isError() else 0.0
            val_t2 = t2.registers[0] if not t2.isError() else 0.0
            val_t3 = t3.registers[0] if not t3.isError() else 0.0
            val_t4 = t4.registers[0] if not t4.isError() else 0.0

            # --- BACA POWER IN (SLAVE 2) ---
            v_in     = konversi_ke_float(modbus_client.read_holding_registers(address=3027, count=2, slave=SLAVE_IN))
            c_in     = konversi_ke_float(modbus_client.read_holding_registers(address=2999, count=2, slave=SLAVE_IN))
            p_in     = konversi_ke_float(modbus_client.read_holding_registers(address=3053, count=2, slave=SLAVE_IN))
            freq     = konversi_ke_float(modbus_client.read_holding_registers(address=3109, count=2, slave=SLAVE_IN))
            pf       = konversi_ke_float(modbus_client.read_holding_registers(address=3077, count=2, slave=SLAVE_IN))
            app_in   = konversi_ke_float(modbus_client.read_holding_registers(address=3069, count=2, slave=SLAVE_IN))
            react_in = konversi_ke_float(modbus_client.read_holding_registers(address=3061, count=2, slave=SLAVE_IN))
            wh_in    = konversi_ke_int64(modbus_client.read_holding_registers(address=3203, count=4, slave=SLAVE_IN))

            # --- BACA POWER OUT (SLAVE 3) ---
            v_out     = konversi_ke_float(modbus_client.read_holding_registers(address=3027, count=2, slave=SLAVE_OUT))
            c_out     = konversi_ke_float(modbus_client.read_holding_registers(address=2999, count=2, slave=SLAVE_OUT))
            p_out     = konversi_ke_float(modbus_client.read_holding_registers(address=3053, count=2, slave=SLAVE_OUT))
            app_out   = konversi_ke_float(modbus_client.read_holding_registers(address=3069, count=2, slave=SLAVE_OUT))
            react_out = konversi_ke_float(modbus_client.read_holding_registers(address=3061, count=2, slave=SLAVE_OUT))
            wh_out    = konversi_ke_int64(modbus_client.read_holding_registers(address=3207, count=4, slave=SLAVE_OUT))
            harm_c    = konversi_ke_float(modbus_client.read_holding_registers(address=21299, count=2, slave=SLAVE_OUT))
            harm_v    = konversi_ke_float(modbus_client.read_holding_registers(address=21329, count=2, slave=SLAVE_OUT))
            
            modbus_client.close()

            # --- UPDATE TEKS DI GUI ---
            ui_vars["t1"].set(f"{val_t1} °C")
            ui_vars["t2"].set(f"{val_t2} °C")
            ui_vars["t3"].set(f"{val_t3} °C")
            ui_vars["t4"].set(f"{val_t4} °C")
            
            ui_vars["v_in"].set(f"{v_in} V")
            ui_vars["v_out"].set(f"{v_out} V")
            ui_vars["c_in"].set(f"{c_in} A")
            ui_vars["c_out"].set(f"{c_out} A")
            ui_vars["p_in"].set(f"{p_in} kW")
            ui_vars["p_out"].set(f"{p_out} kW")
            
            ui_vars["kvar_in"].set(f"{react_in} kVAR")
            ui_vars["kvar_out"].set(f"{react_out} kVAR")
            ui_vars["kva_in"].set(f"{app_in} kVA")
            ui_vars["kva_out"].set(f"{app_out} kVA")
            ui_vars["wh_in"].set(f"{wh_in} Wh")
            ui_vars["wh_out"].set(f"{wh_out} Wh")
            
            ui_vars["harm_c"].set(f"{harm_c} %")
            ui_vars["harm_v"].set(f"{harm_v} %")
            ui_vars["freq"].set(f"{freq} Hz")
            ui_vars["pf"].set(f"{pf}")

            # --- UPDATE DATA GRAFIK ---
            waktu_x.append(len(waktu_x))
            hist_data["t1"].append(val_t1); hist_data["t2"].append(val_t2)
            hist_data["t3"].append(val_t3); hist_data["t4"].append(val_t4)
            hist_data["v_in"].append(v_in); hist_data["v_out"].append(v_out)
            hist_data["c_in"].append(c_in); hist_data["c_out"].append(c_out)
            hist_data["p_in"].append(p_in); hist_data["p_out"].append(p_out)
            
            update_grafik()

            # --- KUMPULKAN DATA OTOMATIS TIAP DETIK ---
            current_data_dict = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Temp 1 (C)": val_t1, "Temp 2 (C)": val_t2, "Temp 3 (C)": val_t3, "Temp 4 (C)": val_t4,
                "Voltage In (V)": v_in, "Voltage Out (V)": v_out,
                "Current In (A)": c_in, "Current Out (A)": c_out,
                "Active Power In (kW)": p_in, "Active Power Out (kW)": p_out,
                "Reactive Power In (kVAR)": react_in, "Reactive Power Out (kVAR)": react_out,
                "Apparent Power In (kVA)": app_in, "Apparent Power Out (kVA)": app_out,
                "Energy In (Wh)": wh_in, "Energy Out (Wh)": wh_out,
                "Harmonic Current (%)": harm_c, "Harmonic Voltage (%)": harm_v,
                "Power Factor": pf, "Frequency (Hz)": freq
            }
            collected_data.append(current_data_dict.copy())
            
        root.after(1000, tick)

    # ---------- Area utama (Layout) ----------
    main = tk.Frame(root, bg=BG_MAIN)
    main.pack(fill="both", expand=True, padx=12, pady=12)
    main.columnconfigure(0, weight=1)
    main.columnconfigure(1, weight=0, minsize=340) 
    main.rowconfigure(0, weight=1)

    # --- Area Charts ---
    charts = tk.Frame(main, bg=BG_MAIN)
    charts.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    for i in range(2):
        charts.columnconfigure(i, weight=1, uniform="c")
        charts.rowconfigure(i, weight=1, uniform="r")

    specs = [
        ("TEMPERATURE", ["Temp1", "Temp2", "Temp3", "Temp4"],
         [("T1", ui_vars["t1"]), ("T2", ui_vars["t2"]), ("T3", ui_vars["t3"]), ("T4", ui_vars["t4"])], "CLEAR", (-5, 100)),
        ("POWER", ["Power In", "Power Out"],
         [("In", ui_vars["p_in"]), ("Out", ui_vars["p_out"])], "CLEAR", (-1, 10)),
        ("VOLTAGE", ["Voltage In", "Voltage Out"],
         [("In", ui_vars["v_in"]), ("Out", ui_vars["v_out"])], "CLEAR", (-10, 300)),
        ("CURRENT", ["Current In", "Current Out"],
         [("In", ui_vars["c_in"]), ("Out", ui_vars["c_out"])], "CLEAR", (-1, 50)),
    ]
    
    for i, (t, ln, ro, bt, yl) in enumerate(specs):
        outer, lines, cv = chart_panel(charts, t, ln, ro, bt, yl)
        outer.grid(row=i // 2, column=i % 2, sticky="nsew",
                   padx=(0, 6) if i % 2 == 0 else (6, 0), pady=(0, 6) if i < 2 else (6, 0))
        all_chart_refs.append((lines, cv))

    # --- Panel Scroll Kanan ---
    side_container = tk.Frame(main, bg=BG_MAIN)
    side_container.grid(row=0, column=1, sticky="nsew")
    
    scrollbar = tk.Scrollbar(side_container, orient="vertical")
    scrollbar.pack(side="right", fill="y")
    side_canvas = tk.Canvas(side_container, bg=BG_MAIN, highlightthickness=0, yscrollcommand=scrollbar.set)
    side_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=side_canvas.yview)
    
    side = tk.Frame(side_canvas, bg=BG_MAIN)
    side_window = side_canvas.create_window((0, 0), window=side, anchor="nw")
    
    side.bind("<Configure>", lambda e: side_canvas.configure(scrollregion=side_canvas.bbox("all")))
    side_canvas.bind("<Configure>", lambda e: side_canvas.itemconfig(side_window, width=e.width))

    def _on_mousewheel(event):
        if event.num == 4 or event.delta > 0:
            side_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            side_canvas.yview_scroll(1, "units")
            
    side_canvas.bind_all("<MouseWheel>", _on_mousewheel)
    side_canvas.bind_all("<Button-4>", _on_mousewheel)
    side_canvas.bind_all("<Button-5>", _on_mousewheel)
    
    param_panel(side, ui_vars).pack(fill="x", pady=(0, 4))
    status_panel(side, 
                 on_manual_save=manual_save_action, 
                 on_clear_charts=clear_charts_action).pack(fill="x", pady=(8, 12))

    # Mulai looping utama
    tick()
    root.mainloop()

if __name__ == "__main__":
    build_gui()