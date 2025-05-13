import cv2
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
from datetime import datetime
import os
import logging
import mediapipe as mp

# TensorFlow ve MediaPipe uyarılarını bastır
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
logging.getLogger('mediapipe').setLevel(logging.ERROR)

class SporHareketApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        
        # MediaPipe yapılandırması
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Kamera ve analiz değişkenleri
        self.video_source = 0
        self.vid = None
        self.analyzing = False
        self.movement_correct = None
        self.prev_movement_state = None # Sayaç için önceki durumu tutar
        
        # Sayaç ve zamanlayıcı
        self.correct_count = 0
        self.timer_running = False
        self.start_time = None
        
        # Hareket konfigürasyonları
        self.movement_types = [
            "Squat", "Push-up", "Lunge",  
            "Bicep Curl", "Shoulder Press"
        ]
        self.current_movement = self.movement_types[0]
        
        # Hedef açılar (eklemdeki açı)
        self.target_angles = {
            "Squat": 90,          # Diz açısı
            "Push-up": 90,        # Dirsek açısı
            "Lunge": 90,          # Ön diz açısı (veya arka diz)
            "Bicep Curl": 30,     # Dirsek açısı (kapanışta)
            "Shoulder Press": 170 # Dirsek açısı (yukarıda)
        }
        self.angle_tolerance = 20 # Açı toleransı (derece)

        # Squat için minimum gövde açısı (omuz-kalça-diz)
        # Bu açı, gövdenin ne kadar dik durduğunu gösterir.
        # Daha büyük bir açı, daha dik bir gövde anlamına gelir.
        # Aşırı öne eğilmeyi engellemek için bir minimum eşik belirleriz.
        self.min_torso_angles = {
            "Squat": 70  # Örnek bir değer, duruma göre ayarlanabilir
        }
        
        # GUI Ayarları
        self.setup_gui()
        
    def setup_gui(self):
        """Arayüz bileşenlerini oluşturur"""
        self.window.geometry("800x750") # Yüksekliği biraz artırdık
        self.window.configure(bg="#f0f0f0")
        
        # Başlık
        tk.Label(self.window, text="SPOR HAREKET ANALİZİ",  
                 font=("Arial", 20, "bold"), bg="#f0f0f0", fg="#2c3e50").pack(pady=10)
        
        # Hareket seçimi
        movement_frame = tk.Frame(self.window, bg="#f0f0f0")
        movement_frame.pack(pady=10)
        
        tk.Label(movement_frame, text="Hareket:", font=("Arial", 12), bg="#f0f0f0").pack(side=tk.LEFT)
        
        self.movement_var = tk.StringVar(value=self.current_movement)
        movement_menu = ttk.Combobox(
            movement_frame,  
            textvariable=self.movement_var,
            values=self.movement_types,
            state="readonly",
            width=15,
            font=("Arial", 12)
        )
        movement_menu.pack(side=tk.LEFT, padx=10)
        movement_menu.bind("<<ComboboxSelected>>", self.change_movement)
        
        # Video görüntüleme
        self.canvas = tk.Canvas(self.window, width=640, height=480, bg="black")
        self.canvas.pack(pady=10)
        
        # Bilgi paneli
        info_frame = tk.Frame(self.window, bg="#f0f0f0")
        info_frame.pack(pady=10)
        
        # Sayaç
        tk.Label(info_frame, text="Doğru Hareket:", font=("Arial", 12), bg="#f0f0f0").grid(row=0, column=0, padx=20)
        self.counter_label = tk.Label(info_frame, text="0", font=("Arial", 24, "bold"), fg="#27ae60", bg="#f0f0f0")
        self.counter_label.grid(row=1, column=0, padx=20)
        
        # Zamanlayıcı
        tk.Label(info_frame, text="Süre:", font=("Arial", 12), bg="#f0f0f0").grid(row=0, column=1, padx=20)
        self.timer_label = tk.Label(info_frame, text="00:00", font=("Arial", 24, "bold"), fg="#2980b9", bg="#f0f0f0")
        self.timer_label.grid(row=1, column=1, padx=20)
        
        # Durum
        self.status_label = tk.Label(self.window, text="Kamerayı Başlatın", font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#34495e")
        self.status_label.pack(pady=(5,10)) # Altına biraz daha boşluk
        
        # Kontrol butonları
        button_frame = tk.Frame(self.window, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        self.btn_start = tk.Button(
            button_frame, text="Başlat", width=12,
            command=self.start_camera, bg="#3498db", fg="white",
            font=("Arial", 12, "bold"), relief=tk.RAISED, borderwidth=2
        )
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_analyze = tk.Button(
            button_frame, text="Analiz Et", width=12,
            command=self.toggle_analysis, bg="#2ecc71", fg="white",
            font=("Arial", 12, "bold"), state=tk.DISABLED, relief=tk.RAISED, borderwidth=2
        )
        self.btn_analyze.pack(side=tk.LEFT, padx=5)
        
        self.btn_reset = tk.Button(
            button_frame, text="Sıfırla", width=12,
            command=self.reset_counter_and_timer, bg="#e67e22", fg="white", # reset_counter -> reset_counter_and_timer
            font=("Arial", 12, "bold"), state=tk.DISABLED, relief=tk.RAISED, borderwidth=2
        )
        self.btn_reset.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(
            button_frame, text="Durdur", width=12,
            command=self.stop_camera, bg="#e74c3c", fg="white",
            font=("Arial", 12, "bold"), state=tk.DISABLED, relief=tk.RAISED, borderwidth=2
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def change_movement(self, event):
        """Seçilen hareketi günceller"""
        self.current_movement = self.movement_var.get()
        self.reset_counter_and_timer() # Sayaç ve zamanlayıcıyı sıfırla
        if self.vid and self.analyzing: # Eğer analiz açıksa ve kamera çalışıyorsa, durumu da sıfırla
             self.status_label.config(text=f"{self.current_movement} bekleniyor...", fg="#34495e")
        elif self.vid:
            self.status_label.config(text="Analizi Başlatın", fg="#34495e")


    def start_camera(self):
        """Kamerayı başlatır"""
        try:
            self.vid = cv2.VideoCapture(self.video_source)
            if not self.vid.isOpened():
                # Alternatif kamera kaynaklarını dene
                for i in range(1, 5):
                    self.vid = cv2.VideoCapture(i)
                    if self.vid.isOpened():
                        self.video_source = i
                        break
                if not self.vid.isOpened():
                    raise RuntimeError(f"Kamera açılamadı (kaynak {self.video_source} ve 1-4 denendi).")
            
            self.btn_start.config(state=tk.DISABLED)
            self.btn_analyze.config(state=tk.NORMAL)
            self.btn_reset.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
            self.status_label.config(text="Analizi Başlatın", fg="#34495e")
            
            self.update_video()
        except Exception as e:
            messagebox.showerror("Hata", f"Kamera başlatılamadı:\n{str(e)}")
            self.status_label.config(text="Kamera Hatası", fg="#e74c3c")
            if self.vid:
                self.vid.release()
                self.vid = None
            self.btn_start.config(state=tk.NORMAL) # Başlat butonunu tekrar aktif et
            self.btn_analyze.config(state=tk.DISABLED)
            self.btn_reset.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.DISABLED)

    def stop_camera(self):
        """Kamerayı durdurur"""
        if self.vid:      
            self.vid.release()
            self.vid = None
            
        self.btn_start.config(state=tk.NORMAL)
        self.btn_analyze.config(state=tk.DISABLED, text="Analiz Et", bg="#2ecc71")
        self.btn_reset.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        
        self.analyzing = False
        self.status_label.config(text="Kamerayı Başlatın", fg="#34495e")
        self.canvas.delete("all") # Kamerayı durdurunca canvası temizle
        self.canvas.create_text(320, 240, text="Kamera Kapalı", fill="white", font=("Arial", 16))


        if self.timer_running:
            self.toggle_timer() # Zamanlayıcıyı durdur
        self.timer_label.config(text="00:00") # Zamanlayıcıyı sıfırla
        self.correct_count = 0 # Sayacı sıfırla
        self.counter_label.config(text="0")


    def toggle_analysis(self):
        """Analiz modunu açıp kapatır"""
        self.analyzing = not self.analyzing
        
        if self.analyzing:
            self.btn_analyze.config(text="Analizi Durdur", bg="#f39c12")
            self.status_label.config(text=f"{self.current_movement} bekleniyor...", fg="#34495e")
            if not self.timer_running:
                self.toggle_timer()
        else:
            self.btn_analyze.config(text="Analiz Et", bg="#2ecc71")
            self.status_label.config(text="Analiz Durduruldu", fg="#34495e")
            # Analiz durduğunda zamanlayıcıyı da durdur
            if self.timer_running:
                self.toggle_timer()
    
    def toggle_timer(self):
        """Zamanlayıcıyı başlatır/durdurur"""
        self.timer_running = not self.timer_running
        
        if self.timer_running:
            self.start_time = datetime.now() - (self.elapsed_time if hasattr(self, 'elapsed_time') and self.elapsed_time else timedelta())
            self.update_timer()
        else:
            # Zamanlayıcı durduğunda geçen süreyi kaydet
            if self.start_time:
                self.elapsed_time = datetime.now() - self.start_time

    def update_timer(self):
        """Zamanlayıcıyı günceller"""
        if self.timer_running and self.start_time:
            elapsed = datetime.now() - self.start_time
            seconds = elapsed.seconds % 60
            minutes = elapsed.seconds // 60
            self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
            self.window.after(1000, self.update_timer)
    
    def reset_counter_and_timer(self):
        """Sayaçları ve zamanlayıcıyı sıfırlar"""
        self.correct_count = 0
        self.counter_label.config(text="0")
        self.prev_movement_state = None # Önceki durumu sıfırla
        
        self.timer_label.config(text="00:00")
        if self.timer_running: # Eğer zamanlayıcı çalışıyorsa
            self.start_time = datetime.now() # Baştan başlat
        else: # Çalışmıyorsa
            self.start_time = None 
            self.elapsed_time = timedelta() # Geçen süreyi de sıfırla

        if self.analyzing:
             self.status_label.config(text=f"{self.current_movement} bekleniyor...", fg="#34495e")


    def update_video(self):
        """Video akışını günceller"""
        if self.vid and self.vid.isOpened():
            ret, frame = self.vid.read()
            
            if ret:
                frame = cv2.flip(frame, 1)
                display_frame = frame.copy() # Çizimler için kopya oluştur
                
                if self.analyzing:
                    self.analyze_frame(frame, display_frame) # display_frame'i de yolla
                
                # Görüntüyü Tkinter formatına çevir
                img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                img = img.resize((640, 480), Image.LANCZOS)
                self.photo = ImageTk.PhotoImage(image=img)
                
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                
                # Bilgileri ekrana yaz (canvas üzerine)
                # self.canvas.create_text(10, 20, text=f"Hareket: {self.current_movement}",  
                #                         anchor=tk.W, fill="yellow", font=("Arial", 12, "bold"))
                
                # Sonraki kareyi planla
                self.window.after(15, self.update_video)
            else:
                # messagebox.showinfo("Video Sonu", "Video akışı sonlandı veya kare okunamadı.")
                self.stop_camera() # Kare okunamıyorsa kamerayı durdur
        # else:
            # self.stop_camera() # vid None ise veya kapalıysa kamerayı durdur

    def analyze_frame(self, frame_to_process, frame_to_draw):
        """Görüntüde hareket analizi yapar ve frame_to_draw üzerine çizer"""
        image_rgb = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False # Performans için
        results = self.pose.process(image_rgb)
        image_rgb.flags.writeable = True # Tekrar yazılabilir yap
        
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                frame_to_draw, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
            )
            
            landmarks = results.pose_landmarks.landmark
            
            # Hareket analizi
            if self.current_movement == "Squat":
                self.analyze_squat(frame_to_draw, landmarks)
            elif self.current_movement == "Push-up":
                self.analyze_pushup(frame_to_draw, landmarks)
            elif self.current_movement == "Lunge":
                self.analyze_lunge(frame_to_draw, landmarks)
            elif self.current_movement == "Bicep Curl":
                self.analyze_bicep_curl(frame_to_draw, landmarks)
            elif self.current_movement == "Shoulder Press":
                self.analyze_shoulder_press(frame_to_draw, landmarks)
            # Diğer hareket analizleri buraya eklenebilir
    
    def calculate_angle(self, a, b, c):
        """Üç nokta arasındaki açıyı (b noktasında) hesaplar"""
        # Noktaların görünür olup olmadığını kontrol et
        if not (a.visibility > 0.5 and b.visibility > 0.5 and c.visibility > 0.5):
            return None # Eğer landmarklardan biri yeterince görünür değilse None döndür

        a = np.array([a.x, a.y])
        b = np.array([b.x, b.y])
        c = np.array([c.x, c.y])
        
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        # Kırpmayı -1 ile 1 arasında yap, np.arccos argümanı bu aralıkta olmalı
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = np.arccos(cosine_angle)
        
        return np.degrees(angle)

    def analyze_squat(self, frame, landmarks):
        """Squat analizi (Bacak açısı ve gövde duruşu)"""
        try:
            # Bacak açısı için landmarklar (Sol taraf)
            hip_l = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            knee_l = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value]
            ankle_l = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
            
            # Gövde açısı için landmarklar (Sol taraf)
            shoulder_l = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]

            # Bacak açısı (Dizdeki açı)
            leg_angle = self.calculate_angle(hip_l, knee_l, ankle_l)
            
            # Gövde açısı (Kalçadaki açı: Omuz-Kalça-Diz)
            # Bu açı, gövdenin femura göre ne kadar dik olduğunu gösterir.
            # Squat sırasında bu açı çok küçülmemeli (aşırı öne eğilme).
            torso_angle = self.calculate_angle(shoulder_l, hip_l, knee_l)

            leg_angle_correct = False
            torso_angle_correct = False

            if leg_angle is not None:
                cv2.putText(frame, f"Bacak: {int(leg_angle)}",  
                            (int(knee_l.x * frame.shape[1]) + 10, int(knee_l.y * frame.shape[0])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 255, 50), 2)
                
                target_leg = self.target_angles["Squat"]
                if target_leg - self.angle_tolerance <= leg_angle <= target_leg + self.angle_tolerance:
                    leg_angle_correct = True
            
            if torso_angle is not None:
                cv2.putText(frame, f"Govde: {int(torso_angle)}",  
                            (int(hip_l.x * frame.shape[1]) - 80, int(hip_l.y * frame.shape[0]) - 20), # Pozisyonu ayarla
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 255, 50) if torso_angle >= self.min_torso_angles["Squat"] else (255,50,50), 2)
                
                min_torso = self.min_torso_angles["Squat"]
                if torso_angle >= min_torso:
                    torso_angle_correct = True

            # Hem bacak açısı hem de gövde açısı doğruysa hareket doğru kabul edilir
            if leg_angle is not None and torso_angle is not None: # İki açı da hesaplanabildiyse
                if leg_angle_correct and torso_angle_correct:
                    self.update_status(True, "DOĞRU")
                elif not leg_angle_correct and torso_angle_correct:
                    self.update_status(False, "BACAK YANLIŞ")
                elif leg_angle_correct and not torso_angle_correct:
                     self.update_status(False, "GÖVDE YANLIŞ")
                else:
                    self.update_status(False, "BACAK & GÖVDE YANLIŞ")
            else: # Eğer açılardan biri veya ikisi de hesaplanamadıysa (landmark görünür değilse)
                self.update_status(False, "Pozisyon Belirsiz")

        except IndexError:
            self.update_status(False, "Landmarklar Eksik")
        except Exception as e:
            # print(f"Squat analiz hatası: {e}")
            self.update_status(False, "Analiz Hatası")


    def analyze_pushup(self, frame, landmarks):
        """Push-up analizi"""
        try:
            # Sol tarafı kullanalım, sağ da kullanılabilir veya ortalaması alınabilir
            shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            elbow = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value]
            wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value]
            
            angle = self.calculate_angle(shoulder, elbow, wrist)
            
            if angle is not None:
                cv2.putText(frame, f"{int(angle)}",  
                            (int(elbow.x * frame.shape[1]) + 10, int(elbow.y * frame.shape[0])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 50), 2)
                
                target = self.target_angles["Push-up"]
                if target - self.angle_tolerance <= angle <= target + self.angle_tolerance:
                    self.update_status(True, "DOĞRU")
                else:
                    self.update_status(False, "AÇI YANLIŞ")
            else:
                self.update_status(False, "Pozisyon Belirsiz")
        except IndexError:
            self.update_status(False, "Landmarklar Eksik")
        except Exception as e:
            self.update_status(False, "Analiz Hatası")


    def analyze_lunge(self, frame, landmarks):
        """Lunge analizi (Ön diz ve Arka diz açıları)"""
        try:
            # Ön bacak (Sol varsayalım, kullanıcıya göre değişebilir)
            hip_l = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
            knee_l = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value]
            ankle_l = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]

            # Arka bacak (Sağ varsayalım)
            hip_r = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
            knee_r = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE.value]
            ankle_r = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]

            front_knee_angle = self.calculate_angle(hip_l, knee_l, ankle_l)
            back_knee_angle = self.calculate_angle(hip_r, knee_r, ankle_r)
            
            # Lunge için genellikle her iki dizin de 90 dereceye yakın olması hedeflenir.
            # Visibility check'i calculate_angle içinde yapılıyor.
            
            front_correct = False
            back_correct = False
            
            target_lunge = self.target_angles["Lunge"]

            if front_knee_angle is not None:
                cv2.putText(frame, f"On: {int(front_knee_angle)}",
                            (int(knee_l.x * frame.shape[1]) + 10, int(knee_l.y * frame.shape[0])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,50), 2)
                if target_lunge - self.angle_tolerance <= front_knee_angle <= target_lunge + self.angle_tolerance:
                    front_correct = True
            
            if back_knee_angle is not None:
                cv2.putText(frame, f"Arka: {int(back_knee_angle)}",
                            (int(knee_r.x * frame.shape[1]) + 10, int(knee_r.y * frame.shape[0])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,50), 2)
                # Arka diz için de benzer bir kontrol, belki tolerans farklı olabilir.
                if target_lunge - self.angle_tolerance <= back_knee_angle <= target_lunge + self.angle_tolerance:
                    back_correct = True

            if front_knee_angle is not None and back_knee_angle is not None:
                if front_correct and back_correct:
                    self.update_status(True, "DOĞRU")
                else:
                    status_msg = []
                    if not front_correct: status_msg.append("ÖN DİZ")
                    if not back_correct: status_msg.append("ARKA DİZ")
                    self.update_status(False, f"{' & '.join(status_msg)} YANLIŞ")
            else:
                self.update_status(False, "Pozisyon Belirsiz")

        except IndexError:
            self.update_status(False, "Landmarklar Eksik")
        except Exception as e:
            self.update_status(False, "Analiz Hatası")


    def analyze_bicep_curl(self, frame, landmarks):
        """Bicep Curl analizi"""
        try:
            shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            elbow = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value]
            wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value]
            
            angle = self.calculate_angle(shoulder, elbow, wrist)

            # Bicep curl için iki aşama olabilir: başlangıç (kol düz) ve bitiş (kol bükülü)
            # Şimdilik sadece bükülü halini (tepe noktası) kontrol edelim.
            # Hedef açı, kolun ne kadar büküldüğünü gösterir (örn: 30 derece çok bükülü)
            
            if angle is not None:
                cv2.putText(frame, f"{int(angle)}",  
                            (int(elbow.x * frame.shape[1]) + 10, int(elbow.y * frame.shape[0])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,50), 2)
                
                target = self.target_angles["Bicep Curl"] # Örneğin 30 derece (tam bükülü)
                # Bicep curl'de hareketin tepe noktasında açı küçük olmalı
                if angle <= target + self.angle_tolerance : # Alt eşik de eklenebilir: angle >= target - self.angle_tolerance
                    self.update_status(True, "DOĞRU (TEPE)")
                # Başlangıç pozisyonu (kol düz) kontrolü de eklenebilir.
                # elif angle >= 160 - self.angle_tolerance: # Kol düzken
                #    self.update_status(False, "BAŞLANGIÇ") # Bu sayılmaz, sadece durum bilgisi
                else:
                    self.update_status(False, "AÇI YANLIŞ")
            else:
                self.update_status(False, "Pozisyon Belirsiz")

        except IndexError:
            self.update_status(False, "Landmarklar Eksik")
        except Exception as e:
            self.update_status(False, "Analiz Hatası")


    def analyze_shoulder_press(self, frame, landmarks):
        """Shoulder Press analizi"""
        try:
            # Dirsek açısı ve omuzun kulak hizasında olup olmadığı kontrol edilebilir.
            shoulder_l = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            elbow_l = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value]
            wrist_l = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value]
            
            # Dirsek açısı
            elbow_angle = self.calculate_angle(shoulder_l, elbow_l, wrist_l)
            
            # Omuzların pozisyonu da önemli olabilir (çok yukarı kalkmaması vb.)
            # Şimdilik sadece dirsek açısına odaklanalım (kollar yukarıdayken)
            
            if elbow_angle is not None:
                cv2.putText(frame, f"Dirsek: {int(elbow_angle)}",  
                            (int(elbow_l.x * frame.shape[1]) + 10, int(elbow_l.y * frame.shape[0])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,50), 2)
                
                target = self.target_angles["Shoulder Press"] # Örneğin 170-180 derece (kollar düz)
                
                # Kollar yukarıdayken (hareketin tepe noktası)
                if elbow_angle >= target - self.angle_tolerance:
                    self.update_status(True, "DOĞRU (TEPE)")
                # Başlangıç pozisyonu (dirsekler 90 derece veya omuz hizası) da kontrol edilebilir.
                # elif abs(elbow_angle - 90) < self.angle_tolerance:
                #     self.update_status(False, "BAŞLANGIÇ")
                else:
                    self.update_status(False, "AÇI YANLIŞ")
            else:
                self.update_status(False, "Pozisyon Belirsiz")

        except IndexError:
            self.update_status(False, "Landmarklar Eksik")
        except Exception as e:
            self.update_status(False, "Analiz Hatası")

    def update_status(self, is_correct_phase, status_message):
        """Durumu günceller ve sayacı artırır"""
        current_time = datetime.now()

        if is_correct_phase:
            self.status_label.config(text=status_message, fg="#27ae60") # Yeşil
            # Sadece "YANLIŞ" durumundan "DOĞRU" durumuna geçişte sayacı artır
            if self.prev_movement_state == False or self.prev_movement_state is None:
                self.correct_count += 1
                self.counter_label.config(text=str(self.correct_count))
            self.movement_correct = True
        else:
            self.status_label.config(text=status_message, fg="#e74c3c") # Kırmızı
            self.movement_correct = False
        
        self.prev_movement_state = self.movement_correct


    def on_closing(self):
        """Pencere kapatılırken temizlik yapar"""
        self.stop_camera()
        if self.pose:
            self.pose.close() # MediaPipe pose modelini serbest bırak
        self.window.destroy()

# Uygulamayı başlat
if __name__ == "__main__":
    from datetime import timedelta # toggle_timer ve reset_counter_and_timer için eklendi
    root = tk.Tk()
    app = SporHareketApp(root, "Spor Hareket Analiz Uygulaması v2.0")
    root.mainloop()