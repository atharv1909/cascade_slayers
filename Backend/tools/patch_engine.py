with open('D:/B.Tech/Hackathons/Cascade/Backend/api/engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_block = '''            # Load cached events from disk
            events_path = os.path.join(self.root_dir, "runs", scenario_id, fault_profile, "events.json")
            if os.path.exists(events_path):
                with open(events_path, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
                self._cached_events = [CanonicalEvent(**item) for item in raw_list]
            else:
                self._cached_events = []'''

new_block = '''            # Load cached events from disk or generate on the fly via Digital Twin
            events_gz = os.path.join(self.root_dir, "runs", scenario_id, fault_profile, "events.json.gz")
            events_path = os.path.join(self.root_dir, "runs", scenario_id, fault_profile, "events.json")

            raw_list = None
            if os.path.exists(events_gz):
                import gzip
                with gzip.open(events_gz, "rt", encoding="utf-8") as f:
                    raw_list = json.load(f)
            elif os.path.exists(events_path):
                with open(events_path, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
            else:
                from sim.core import CityDigitalTwin
                from sim.observe import generate_canonical_events
                from harness.faults import FaultInjector
                from harness.paths import get_config_path
                
                city_file = "heldout_city.yaml" if city == "heldout_city" else "mumbai.yaml"
                city_cfg_path = get_config_path(f"cities/{city_file}")
                plugin_cfg_path = get_config_path(f"plugins/{scenario_id}.yaml")
                if os.path.exists(city_cfg_path) and os.path.exists(plugin_cfg_path):
                    twin = CityDigitalTwin(city_cfg_path, plugin_cfg_path, seed=42)
                    truth_df, fc_df, g_true = twin.run_episode()
                    start_dt = datetime(2026, 7, 26, 0, 0, 0, tzinfo=timezone.utc)
                    clean_events = generate_canonical_events(truth_df, fc_df, start_dt, np.random.default_rng(42))
                    injector = FaultInjector()
                    faulty_events = injector.apply_faults(clean_events, profile_name=fault_profile, seed=42)
                    raw_list = [e.model_dump(mode="json") for e in faulty_events]

            if raw_list:
                self._cached_events = [CanonicalEvent(**item) for item in raw_list]
            else:
                self._cached_events = []'''

text = text.replace(old_block.replace('\r\n', '\n'), new_block.replace('\r\n', '\n'))
with open('D:/B.Tech/Hackathons/Cascade/Backend/api/engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Successfully enhanced api/engine.py scenario loader')
