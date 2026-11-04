# 🎯 CrossPro - Ultimate Crosshair Pro

> **100% 칼사각 & 완전 대칭 조준선부터, 그림판급 수제 픽셀 브러시 스튜디오, 자동 업데이트까지 탑재한 최강의 FPS 게이밍 오버레이 시스템**

[![Release](https://img.shields.io/github/v/release/OKHDEV/CrossPro?color=FF6B00&label=Release)](https://github.com/OKHDEV/CrossPro/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)](https://github.com/OKHDEV/CrossPro)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ⚡ 주요 특징 (Key Features)

- **🎯 100% 칼사각 & 수학적 완전 대칭 (Pure Solid)**:
  - 흐려짐 및 불투명도 왜곡 0% 차단.
  - 0.1px 단위 미세 조절에도 상하좌우 4방향 간격이 1픽셀도 어긋나지 않고 화면 정중앙에 완전 고정됩니다.
- **🎨 픽셀 브러시 스튜디오 (Pixel Brush Studio)**:
  - 1px 초미세 연필부터 512×512 사진급 해상도까지 지원.
  - 실시간 좌클릭 그리기, 우클릭 지우개, 격자선 토글, 퀵 색상 팔레트.
- **🌊 스무스 사진 모드 & 칼사각 도트 모드**:
  - 가장자리가 부드러운 안티앨리어싱 스무스 펜 모드와 선명한 칼사각 도트 펜 모드를 자유자재로 선택.
- **👁️ 모니터 1:1 실물 라이브 미니 프리뷰 (80×80)**:
  - 작업창 바로 옆에 모니터 화면에 실제로 찍히는 100% 실물 크기 창을 제공하여 실시간으로 확인하며 제작.
- **🚀 로고 스플래시 & 자동 업데이트 (Auto-Updater)**:
  - 프로그램 실행 시 세련된 로고와 함께 GitHub 최신 버전을 자동으로 감지하여 원클릭으로 최신 상태 유지.
- **💥 발사 애니메이션 (Firing Animation)**:
  - 마우스 좌클릭 사격 시 실시간으로 크로스헤어가 벌어지고 복귀하는 동적 사격 반응 효과.
- **🏆 프로게이머 프리셋 내장**:
  - TenZ, Yay, Demon1, Aspas 등 프로게이머 공식 세팅 원클릭 로드 및 커스텀 프로필 무제한 저장.
- **🛡️ 100% 안전한 오버레이 & 트레이 제어**:
  - 게임 메모리를 변조하지 않는 투명 윈도우 오버레이 방식으로 안티치트 100% 안전.
  - 작업표시줄 숨겨진 아이콘(트레이)에서 우클릭으로 언제든 안전 종료 지원.

---

## ⌨️ 단축키 안내 (Global Keybinds)

| 단축키 | 기능 설명 |
|---|---|
| **F8** | 화면 크로스헤어 표시 / 숨기기 토글 |
| **F9** | CrossPro 설정창 열기 / 닫기 (트레이 최소화) |
| **F10** | 다음 조준선 프로필로 즉시 전환 |
| **Ctrl + F12** | 프로그램 완전 종료 |

---

## ⬇️ 다운로드 (Download)

최신 버전의 무설치 단독 실행 파일(`.exe`)은 아래 링크에서 바로 다운로드할 수 있습니다:

👉 **[CrossPro 최신 버전 다운로드](https://github.com/OKHDEV/CrossPro/releases/latest/download/CrossPro.exe)**  
👉 **[공식 배포 웹사이트 방문하기](https://okhdev.github.io/CrossPro/)**

---

## 🛠️ 개발 및 빌드 (Development)

```bash
# 레포지토리 클론
git clone https://github.com/OKHDEV/CrossPro.git
cd CrossPro

# 의존 패키지 설치
pip install pillow pystray

# 실행
python crosspro.py

# 단독 실행 파일 빌드
python -m PyInstaller --onefile --noconsole --clean --icon=icon.ico --add-data "icon.ico;." --name CrossPro crosspro.py
```

---

## 📄 라이선스 (License)

This project is licensed under the MIT License.
