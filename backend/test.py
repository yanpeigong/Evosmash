import os
import sys
import time

import requests

# === Configuration ===
SERVER_URL = "http://127.0.0.1:8000"
TEST_VIDEO_PATH = "test.mp4"  # Make sure a real badminton video exists at this path.


# === Terminal Color Codes ===
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}")


def print_info(key, value):
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {key}: {Colors.BOLD}{value}{Colors.ENDC}")


def print_success(text):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} {text}")


def print_ai(text):
    print(f"{Colors.YELLOW}[AI COACH]{Colors.ENDC} 🗣️  \"{text}\"")


def check_server():
    """Check whether the backend is reachable."""
    try:
        requests.get(f"{SERVER_URL}/", timeout=2)
        print_success("Backend server is reachable.")
        return True
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}[ERROR] Unable to connect to {SERVER_URL}{Colors.ENDC}")
        print("Make sure you have started the backend with 'python main.py'.")
        return False


def simulate_rally(video_path, mode='singles'):
    """
    Simulate one full rally analysis.

    Returns:
        session_id if manual feedback may be needed, otherwise None.
    """
    if not os.path.exists(video_path):
        print(f"{Colors.RED}[ERROR] Video file not found: {video_path}{Colors.ENDC}")
        return None

    print_header("Step 1: Upload a clip and run full-pipeline analysis")
    print(f"Uploading {video_path} ...")

    start_time = time.time()

    try:
        with open(video_path, 'rb') as file_obj:
            files = {'file': file_obj}
            data = {'match_type': mode}
            response = requests.post(f"{SERVER_URL}/analyze_rally", files=files, data=data)

        if response.status_code != 200:
            print(f"{Colors.RED}Server error: {response.text}{Colors.ENDC}")
            return None

        result = response.json()

        physics = result['physics']
        advice = result['advice']
        if isinstance(advice, dict):
            advice = advice.get('text', '')
        tactics = result['tactics']
        session_id = result['session_id']

        auto_result = result.get('auto_result', 'UNKNOWN')
        auto_reward = result.get('auto_reward', 0.0)

        elapsed = time.time() - start_time
        print(f"Analysis completed in: {elapsed:.2f}s")

        print_header("Step 2: Physics and tactical decision output")
        print_info("Event", physics['event'])
        print_info("Max Speed", f"{physics['max_speed_kmh']} km/h")
        print_info("Description", physics['description'])
        print("-" * 30)
        print_ai(advice)
        print("-" * 30)

        print(f"{Colors.BLUE}[Thompson Sampling Trace]{Colors.ENDC}")
        for idx, tactic in enumerate(tactics):
            meta = tactic['metadata']
            tactic_id_disp = meta.get('tactic_id') or meta.get('id')
            alpha = meta.get('alpha', 1.0)
            beta = meta.get('beta', 1.0)
            score = tactic.get('score', 0.0)

            total = alpha + beta
            win_rate = (alpha / total * 100) if total > 0 else 0.0

            prefix = "->" if tactic_id_disp == session_id else "  "
            print(f"{prefix} {idx + 1}. ID:{tactic_id_disp} | Win Rate:{win_rate:.1f}% (alpha={alpha:.1f}, beta={beta:.1f}) | Score:{score:.2f}")

        print_header("Step 3: Auto-referee and evolution status")

        if auto_result != 'UNKNOWN':
            color = Colors.GREEN if auto_result == 'WIN' else Colors.RED
            print(f"Auto-referee result: {color}{Colors.BOLD}{auto_result}{Colors.ENDC}")

            if abs(auto_reward) > 0:
                print(f"Evolution reward applied: {Colors.BOLD}{auto_reward}{Colors.ENDC}")
                print(f"{Colors.GREEN}>> No manual feedback required. Closed loop complete. <<{Colors.ENDC}")
                return None

            print("A result was produced, but no reward update was triggered.")
            return session_id

        print(f"{Colors.YELLOW}Warning: the auto-referee could not determine the landing point (Result: UNKNOWN){Colors.ENDC}")
        print("Switching to manual feedback mode.")
        return session_id

    except Exception as error:
        print(f"{Colors.RED}Request failed: {error}{Colors.ENDC}")
        return None


def manual_feedback(tactic_id):
    """Send manual correction feedback when the referee is uncertain."""
    if not tactic_id:
        print("Error: no valid tactic ID is available for feedback.")
        return

    print(f"\n{Colors.CYAN}>>> Entering manual feedback mode (ID: {tactic_id}) <<<{Colors.ENDC}")
    result = None
    while True:
        choice = input("Did this rally end in a win? (w=win, l=loss, n=skip): ").lower()
        if choice == 'w':
            result = 'WIN'
            break
        if choice == 'l':
            result = 'LOSS'
            break
        if choice == 'n':
            return

    try:
        payload = {'tactic_id': tactic_id, 'result': result}
        response = requests.post(f"{SERVER_URL}/feedback", data=payload)
        if response.status_code == 200:
            feedback_result = response.json()
            print_success(f"Manual correction saved. Reward: {feedback_result['reward']}")
            print(f"{Colors.GREEN}>> Model parameters were updated manually. <<{Colors.ENDC}")
        else:
            print(f"Feedback failed: {response.text}")
    except Exception as error:
        print(f"Feedback error: {error}")


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Colors.BOLD}EvoSmash Auto Simulator v2.1{Colors.ENDC}")

    if not check_server():
        sys.exit(1)

    while True:
        session_id_to_feedback = simulate_rally(TEST_VIDEO_PATH, mode='singles')

        if session_id_to_feedback:
            manual_feedback(session_id_to_feedback)

        print("\n" + "=" * 50 + "\n")
        cont = input("Press Enter to simulate the next rally (n to quit): ")
        if cont.lower() == 'n':
            break
