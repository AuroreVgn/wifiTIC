"""Import WiFiTIC daily power history into HA hourly long-term statistics."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import logging
import re
from zoneinfo import ZoneInfo

from homeassistant.components.recorder.statistics import async_add_external_statistics, valid_statistic_id
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.const import UnitOfEnergy
from homeassistant.components.recorder import get_instance

_LOGGER = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Europe/Paris")


def _timestamp(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def parse_day(payload):
    """Parse API v2 (timestamps row) or v3 (timestamp, power pairs)."""
    version = int(payload.get("version", 2))
    headers = payload.get("headers") or []
    data = payload.get("data") or []
    result = defaultdict(list)
    if version not in (2, 3):
        raise ValueError(f"Unsupported WiFiTIC history version {version}")
    if version == 3:
        for idx, series in enumerate(data):
            name = str(headers[idx]) if idx < len(headers) else f"serie_{idx+1}"
            for item in series:
                if not isinstance(item, (list, tuple)) or len(item) < 2: continue
                try: result[name].append((_timestamp(item[0]), float(item[1])))
                except (TypeError, ValueError, OverflowError): continue
    elif data:
        timestamps = data[0]
        for idx, series in enumerate(data[1:]):
            name = str(headers[idx]) if idx < len(headers) else f"serie_{idx+1}"
            for ts, power in zip(timestamps, series):
                try: result[name].append((_timestamp(ts), float(power)))
                except (TypeError, ValueError, OverflowError): continue
    return result


def _hourly_energy(points):
    """Integrate known successive samples; do not extrapolate the final sample."""
    points = sorted(set(points), key=lambda item: item[0])
    hours = defaultdict(float)
    for (start, watts), (end, _) in zip(points, points[1:]):
        seconds = (end - start).total_seconds()
        # Avoid treating outages/gaps as continuous consumption.
        if not 0 < seconds <= 3600 or watts < 0: continue
        at = start
        while at < end:
            hour = at.replace(minute=0, second=0, microsecond=0)
            next_hour = hour + timedelta(hours=1)
            stop = min(end, next_hour)
            hours[hour] += watts * (stop - at).total_seconds() / 3_600_000
            at = stop
    return hours


async def _existing_sums(hass, statistic_id, start, end):
    """Read stored hourly statistics through the Recorder executor.

    Import lazily: a Recorder API change must not prevent WiFiTIC startup.
    """
    from homeassistant.components.recorder import statistics as recorder_statistics

    reader = getattr(recorder_statistics, "statistics_during_period", None)
    if reader is None:
        raise RuntimeError(
            "Recorder statistics_during_period unavailable: import cancelled safely"
        )
    data = await get_instance(hass).async_add_executor_job(
        reader, hass, start, end, [statistic_id], "hour", None, {"sum"}
    )
    return data.get(statistic_id, [])


def _statistic_id(entry_id: str, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_") or "energy"
    safe_entry_id = re.sub(r"[^a-z0-9]+", "_", entry_id.casefold()).strip("_")
    return f"wifitic:{safe_entry_id}_{slug}"


def _row_start(row):
    value = row["start"]
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(float(value), timezone.utc)


async def _fetch_days(api, start: date, end: date):
    """Preflight ALL days before touching Recorder: no partial writes on API errors."""
    points = defaultdict(list)
    day = start
    loaded = 0
    while day <= end:
        try:
            payload = await api.history_day(day.year, day.timetuple().tm_yday)
            parsed = parse_day(payload)
            if not parsed:
                raise ValueError("empty history")
        except Exception as exc:
            raise ValueError(f"WiFiTIC history unavailable for {day}: {exc}") from exc
        for name, samples in parsed.items():
            points[name].extend(samples)
        loaded += 1
        day += timedelta(days=1)
    return points, loaded


async def import_history(hass, api, entry_id: str, start: date, end: date):
    """Safely replace a selected range and automatically rebuild later sums.

    When the user reimports old days, fetch all intervening days through the
    last existing statistic, recomputing a continuous sum from the preceding
    Recorder value. Abort before writes if any source day cannot be fetched.
    """
    if start > end:
        raise ValueError("start_date must not be after end_date")
    if end >= datetime.now(LOCAL_TZ).date():
        raise ValueError("Only completed days can be imported")
    if (end - start).days > 366:
        raise ValueError("Import a maximum of 367 days per request")

    requested_end = end
    points, loaded = await _fetch_days(api, start, end)

    # Discover existing later statistics for each series. If a series extends
    # beyond the selected period, rebuild all the intervening days as well.
    # This avoids changing earlier sums while leaving later sums at old offsets.
    now = datetime.now(timezone.utc) + timedelta(hours=1)
    expanded_end = end
    for name, samples in points.items():
        hours = _hourly_energy(samples)
        if not hours:
            continue
        sid = _statistic_id(entry_id, name)
        if not valid_statistic_id(sid):
            raise ValueError(f"Invalid statistic ID: {sid}")
        later = await _existing_sums(
            hass, sid, max(hours) + timedelta(hours=1), now
        )
        if later:
            last = max(_row_start(row) for row in later)
            expanded_end = max(expanded_end, last.astimezone(LOCAL_TZ).date())

    if expanded_end >= datetime.now(LOCAL_TZ).date():
        raise ValueError("Existing statistics extend into today; cannot safely rebuild")
    if (expanded_end - start).days > 366:
        raise ValueError("Rebuilding the existing range would exceed 367 days")
    if expanded_end > end:
        _LOGGER.info(
            "WiFiTIC reimport %s..%s: extending to %s to preserve Recorder sums",
            start, requested_end, expanded_end,
        )
        end = expanded_end
        points, loaded = await _fetch_days(api, start, end)

    # Prepare every series before the first write. Avoid partial changes on
    # validation or Recorder read failures.
    prepared = []
    for name, samples in points.items():
        hours = _hourly_energy(samples)
        if not hours:
            continue
        sid = _statistic_id(entry_id, name)
        if not valid_statistic_id(sid):
            raise ValueError(f"Invalid statistic ID: {sid}")
        first_hour, last_hour = min(hours), max(hours)
        later = await _existing_sums(hass, sid, last_hour + timedelta(hours=1), now)
        if later:
            raise ValueError(
                f"{sid}: later statistics remain after {last_hour.isoformat()}; "
                "import cancelled without changes"
            )
        earlier = await _existing_sums(
            hass, sid, first_hour - timedelta(days=3660), first_hour
        )
        prior = [row for row in earlier if row.get("sum") is not None
                 and _row_start(row) < first_hour]
        prior.sort(key=_row_start)
        total = float(prior[-1]["sum"]) if prior else 0.0
        rows = []
        for hour, energy in sorted(hours.items()):
            total += energy
            rows.append(StatisticData(start=hour, state=energy, sum=total))
        meta = StatisticMetaData(
            has_mean=False, has_sum=True, name=f"WiFiTIC {name}",
            source="wifitic", statistic_id=sid,
            unit_class="energy", unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )
        prepared.append((name, sid, meta, rows))

    imported = 0
    statistic_ids = {}
    for name, sid, meta, rows in prepared:
        async_add_external_statistics(hass, meta, rows)
        statistic_ids[name] = sid
        imported += len(rows)
    return {
        "days_loaded": loaded,
        "days_failed": [],
        "series": len(statistic_ids),
        "hours_imported": imported,
        "statistic_ids": statistic_ids,
        "requested_end_date": requested_end.isoformat(),
        "effective_end_date": end.isoformat(),
        "range_extended": end > requested_end,
        "production_series": {k: v for k, v in statistic_ids.items()
                              if "production" in k.casefold()},
    }

# REST labels are deliberately mapped by name, never by series position.
# The last two labels are retained for backwards compatibility with old
# Zen Flex entity IDs ("pointe").
def _native_target_key(name: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()
    aliases = {
        "heures creuses jour normal": "index_1",
        "heures pleines jour normal": "index_2",
        "heures creuses sobriete": "index_3",
        "heures pleines sobriete": "index_4",
        "heures creuses pointe": "index_3",
        "heures pleines pointe": "index_4",
        "production": "production_index",
    }
    import unicodedata
    normalized = "".join(ch for ch in unicodedata.normalize("NFKD", normalized) if not unicodedata.combining(ch))
    return aliases.get(normalized)


def _row_sum(row):
    value = row.get("sum")
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _overlap_ranges(hour_set):
    """Compress an hour set into inclusive UTC intervals."""
    if not hour_set:
        return []
    ordered = sorted(hour_set)
    intervals = []
    first = last = ordered[0]
    for hour in ordered[1:]:
        if hour - last == timedelta(hours=1):
            last = hour
        else:
            intervals.append({"first_hour_utc": first.isoformat(), "last_hour_utc": last.isoformat()})
            first = last = hour
    intervals.append({"first_hour_utc": first.isoformat(), "last_hour_utc": last.isoformat()})
    return intervals


def _migration_plan(hours, stored_in_range, all_stored, unit):
    """Read-only, conservative junction plan for REST hourly energy and MQTT sums.

    A baseline adjustment is only a candidate, never an approved Recorder write.
    A gap or mixed coverage must block automatic migration.
    """
    factor = 1000 if unit == "Wh" else (1 if unit == "kWh" else None)
    recorded = {_row_start(row): row for row in all_stored}
    existing_hours = sorted(recorded)
    rest_hours = set(hours)
    overlapping = rest_hours & set(existing_hours)
    missing = rest_hours - set(existing_hours)
    earliest = existing_hours[0] if existing_hours else None
    latest = existing_hours[-1] if existing_hours else None
    prior = sorted(t for t in missing if earliest is None or t < earliest)
    inside_or_after = sorted(t for t in missing if earliest is not None and t >= earliest)
    prior_energy = sum(hours[t] for t in prior)
    # Compare successive hourly REST energy with Recorder delta(sum) ONLY
    # when both hours have REST samples and Recorder sums.
    differences = []
    for t in sorted(overlapping):
        previous = t - timedelta(hours=1)
        if previous not in overlapping:
            continue
        curr_sum = _row_sum(recorded[t])
        prev_sum = _row_sum(recorded[previous])
        if curr_sum is None or prev_sum is None or factor is None:
            continue
        mqtt_delta = (curr_sum - prev_sum) / factor
        rest_delta = hours[t]
        if abs(mqtt_delta - rest_delta) > 0.05:
            differences.append({
                "hour_utc": t.isoformat(),
                "rest_kwh": round(rest_delta, 6),
                "mqtt_delta_kwh": round(mqtt_delta, 6),
                "difference_kwh": round(rest_delta - mqtt_delta, 6),
            })
    first_row = recorded[earliest] if earliest is not None else None
    first_sum = _row_sum(first_row) if first_row else None
    # Detect uncovered hours at the REST/MQTT junction. Absence of REST
    # tariff samples is not necessarily an energy gap (inactive tariff).
    last_prior = max(prior) if prior else None
    junction_gap = (
        int((earliest - last_prior).total_seconds() // 3600) - 1
        if earliest is not None and last_prior is not None else None
    )
    blockers = []
    if factor is None: blockers.append("unknown_sensor_unit")
    if earliest is None: blockers.append("no_existing_mqtt_statistics")
    if inside_or_after: blockers.append("missing_hours_inside_or_after_mqtt_history")
    if differences: blockers.append("rest_mqtt_hourly_discrepancies")
    if first_sum is None and earliest is not None: blockers.append("missing_mqtt_sum")
    if junction_gap is not None and junction_gap > 0:
        blockers.append("unverified_junction_gap")
    # Recorder-managed statistics cannot be safely rewritten by the external
    # statistics API. Therefore the plan is NEVER an automatic go-ahead.
    blockers.append("native_recorder_sum_rewrite_requires_validated_method")
    return {
        "first_mqtt_hour_utc": earliest.isoformat() if earliest else None,
        "last_mqtt_hour_utc": latest.isoformat() if latest else None,
        "first_mqtt_sum": first_sum,
        "first_mqtt_sum_unit": unit,
        "rest_hours_before_first_mqtt": len(prior),
        "rest_energy_before_first_mqtt_kwh": round(prior_energy, 6),
        "candidate_sum_shift_in_sensor_unit": round(prior_energy * factor, 6) if factor is not None else None,
        "candidate_first_mqtt_sum_after_shift": round(first_sum + prior_energy * factor, 6) if first_sum is not None and factor is not None else None,
        "missing_hours_inside_or_after_mqtt": len(inside_or_after),
        "junction_unverified_hours": junction_gap,
        "overlap_comparisons": len(overlapping) and sum(1 for t in overlapping if t-timedelta(hours=1) in overlapping) or 0,
        "overlap_discrepancy_count": len(differences),
        "overlap_discrepancies_sample": differences[:10],
        "blockers": blockers,
        "automatic_migration_allowed": False,
        "note": "Candidate shift is informational, not a safe Recorder mutation. "
                "Tariff inactivity can create apparent gaps. The first MQTT "
                "sum is Recorder-managed and must be preserved by a validated migration procedure.",
    }


async def preview_history(hass, api, entry_id: str, start: date, end: date):
    """Read-only REST/Recorder overlap audit; never write statistics.

    A safe preview is NOT a migration approval: current MQTT sums are
    Recorder-managed and cannot be overwritten with external statistics.
    """
    from homeassistant.helpers import entity_registry as er

    if start > end:
        raise ValueError("start_date must not be after end_date")
    if end >= datetime.now(LOCAL_TZ).date():
        raise ValueError("Only completed days can be previewed")
    if (end - start).days > 366:
        raise ValueError("Preview a maximum of 367 days")

    points, loaded = await _fetch_days(api, start, end)
    registry = er.async_get(hass)
    available = []
    entities_by_key = {}
    for entity in er.async_entries_for_config_entry(registry, entry_id):
        if entity.domain != "sensor":
            continue
        matched_key = next((key for key in ("production_index", *(f"index_{i}" for i in range(1, 7)))
                            if entity.unique_id == f"{entry_id}_{key}"), None)
        if matched_key is None:
            continue
        state = hass.states.get(entity.entity_id)
        item = {
            "entity_id": entity.entity_id,
            "statistic_id": entity.entity_id,
            "unique_id": entity.unique_id,
            "unit": state.attributes.get("unit_of_measurement") if state else None,
            "state_class": state.attributes.get("state_class") if state else None,
            "current_state": state.state if state else None,
        }
        available.append(item)
        entities_by_key[matched_key] = item
    available.sort(key=lambda item: item["unique_id"])

    # Read one full hourly interval for each series. The UTC bounds are derived
    # from REST hours, not from a fixed 24-hour local-day assumption (DST).
    series = []
    for name, samples in sorted(points.items()):
        hours = _hourly_energy(samples)
        target_key = _native_target_key(name)
        target = entities_by_key.get(target_key) if target_key else None
        record = {
            "source": name,
            "legacy_statistic_id": _statistic_id(entry_id, name),
            "target_statistic_id": target["statistic_id"] if target else None,
            "target_entity_id": target["entity_id"] if target else None,
            "mapping": "matched" if target else ("entity_missing" if target_key else "unknown_source"),
            "hours": len(hours),
            "energy_kwh": round(sum(hours.values()), 6),
            "first_hour_utc": min(hours).isoformat() if hours else None,
            "last_hour_utc": max(hours).isoformat() if hours else None,
            "recorder": None,
            "migration_ready": False,
        }
        if not hours:
            record["status"] = "no_usable_hourly_data"
            series.append(record)
            continue
        if target is None:
            record["status"] = "mapping_required"
            series.append(record)
            continue
        sid = target["statistic_id"]
        # This reads the existing MQTT series, including all hours in the
        # requested REST interval. A statistic can exist without an entity state.
        stored = await _existing_sums(hass, sid, min(hours), max(hours) + timedelta(hours=1))
        stored_by_hour = {_row_start(row): row for row in stored}
        rest_hours = set(hours)
        recorded_hours = set(stored_by_hour)
        overlap = rest_hours & recorded_hours
        missing = rest_hours - recorded_hours
        recorder_only = recorded_hours - rest_hours
        sums = [(t, _row_sum(row)) for t, row in sorted(stored_by_hour.items())]
        usable_sums = [(t, val) for t, val in sums if val is not None]
        decreasing = [t.isoformat() for (_, prev), (t, cur) in zip(usable_sums, usable_sums[1:])
                      if cur < prev - 1e-6]
        # MQTT statistic sums have their own baseline. Compare monotonicity,
        # never assume REST kWh can be directly appended to a Recorder sum.
        unit = target.get("unit")
        # Query beyond the selected REST dates to locate the actual MQTT
        # junction, including statistics recorded after the requested period.
        # This intentionally does not change the earlier in-range overlap report.
        all_stored = await _existing_sums(
            hass, sid, min(hours), datetime.now(timezone.utc) + timedelta(hours=1)
        )
        record["migration_plan"] = _migration_plan(hours, stored, all_stored, unit)
        record["recorder"] = {
            "statistic_id": sid,
            "sensor_unit": unit,
            "rest_energy_unit": "kWh",
            "conversion_to_sensor_unit": 1000 if unit == "Wh" else (1 if unit == "kWh" else None),
            "existing_hours_in_range": len(recorded_hours),
            "overlapping_hours": len(overlap),
            "missing_hours": len(missing),
            "recorder_only_hours": len(recorder_only),
            "missing_energy_kwh": round(sum(hours[t] for t in missing), 6),
            "overlap_energy_kwh": round(sum(hours[t] for t in overlap), 6),
            "first_existing_hour_utc": min(recorded_hours).isoformat() if recorded_hours else None,
            "last_existing_hour_utc": max(recorded_hours).isoformat() if recorded_hours else None,
            "first_existing_sum": usable_sums[0][1] if usable_sums else None,
            "last_existing_sum": usable_sums[-1][1] if usable_sums else None,
            "missing_intervals": _overlap_ranges(missing),
            "overlap_intervals": _overlap_ranges(overlap),
            "decreasing_sum_hours": decreasing,
        }
        if unit not in ("Wh", "kWh"):
            record["status"] = "unit_verification_required"
        elif target.get("state_class") != "total_increasing":
            record["status"] = "state_class_verification_required"
        elif decreasing:
            record["status"] = "recorder_sum_anomaly"
        elif overlap:
            record["status"] = "overlap_detected"
        elif missing:
            record["status"] = "missing_hours_detected"
        else:
            record["status"] = "no_missing_hours"
        series.append(record)

    return {
        "dry_run": True,
        "recorder_modified": False,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days_loaded": loaded,
        "available_mqtt_entities": available,
        "historical_series": series,
        "migration_ready": False,
        "note": "Read-only analysis of existing hourly MQTT statistics. "
                "Missing sobriety series are normal when counters did not change. "
                "No writes or automatic migration approval; native Recorder sums "
                "require a separately validated migration strategy.",
    }


async def merge_native_consumption_history(hass, api, entry_id: str, start: date, end: date, confirm_write: bool = False, include_injection: bool = False, include_consumption: bool = True):
    """Merge completed REST tariff history into native MQTT counters.

    Only the contiguous pre-MQTT part of each tariff is eligible. This is
    deliberately independent per tariff and refuses ambiguous boundaries.
    """
    from homeassistant.components.recorder import statistics as rs
    from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
    from homeassistant.helpers import entity_registry as er
    from functools import partial

    if start > end or end >= datetime.now(LOCAL_TZ).date() or (end-start).days > 366:
        raise ValueError("Choose completed dates (maximum 367 days)")
    points, days = await _fetch_days(api, start, end)
    registry = er.async_get(hass)
    entity_by_key = {e.unique_id.removeprefix(entry_id + "_"): e.entity_id
                     for e in er.async_entries_for_config_entry(registry, entry_id)
                     if e.domain == "sensor" and (e.unique_id.startswith(entry_id + "_index_") or e.unique_id == entry_id + "_production_index")}
    by_key = {}
    for label, samples in points.items():
        key = _native_target_key(label)
        if key is None or (key == "production_index" and not include_injection) or (key.startswith("index_") and not include_consumption):
            continue
        if key in by_key:
            raise ValueError(f"Multiple REST series mapped to {key}; aborting")
        by_key[key] = (label, _hourly_energy(samples))
    if not by_key:
        raise ValueError("No matching REST energy series for selected types")
    result = []
    prepared = []
    now = datetime.now(timezone.utc) + timedelta(hours=2)
    for key, (label, hours) in sorted(by_key.items()):
        if not hours:
            result.append({"tariff": label, "status": "no_samples"}); continue
        sid = entity_by_key.get(key)
        if not sid:
            raise ValueError(f"Missing native MQTT sensor for {label} ({key})")
        state = hass.states.get(sid)
        if not state or state.attributes.get("unit_of_measurement") != "Wh" or state.attributes.get("state_class") != "total_increasing":
            raise ValueError(f"{sid}: expected Wh total_increasing sensor")
        native_data = await get_instance(hass).async_add_executor_job(
            rs.statistics_during_period, hass, min(hours)-timedelta(hours=1), now,
            [sid], "hour", None, {"state", "sum"})
        native = sorted(native_data.get(sid, []), key=_row_start)
        if not native:
            raise ValueError(f"{sid}: native statistics missing")
        boundary = _row_start(native[0])
        # Refuse any overlapping REST interval, including an existing native
        # migration, instead of silently replacing a previously imported row.
        prior = {t: val for t, val in hours.items() if t < boundary}
        overlap = [t for t in hours if t >= boundary]
        if overlap:
            # The REST endpoint may include dates after MQTT started. Those
            # values are not used, but we report the exclusion explicitly.
            pass
        if not prior:
            result.append({"tariff": label, "statistic_id": sid,
                           "status": "already_present_or_no_pre_mqtt_history",
                           "first_native_utc": boundary.isoformat()}); continue
        # A nonzero initial sum can indicate that the series was previously
        # migrated. Never apply the baseline adjustment a second time.
        # Overlap between REST and native rows is permitted only after boundary;
        # pre-boundary native data is never replaced.
        if any(_row_start(r) < boundary for r in native):
            raise ValueError(f"{sid}: unexpected native rows before boundary")
        if native[0].get("state") is None or native[0].get("sum") is None:
            raise ValueError(f"{sid}: native first state or sum missing")
        first_index = float(native[0]["state"])
        first_sum = float(native[0]["sum"])
        # The initial MQTT sum is not necessarily zero. Preserve its existing
        # offset and add only the historical energy to the whole native series.
        # Idempotency is enforced by refusing any native row before boundary;
        # never infer from a nonzero sum alone that history was already merged.
        if not (-0.000001 <= first_sum < float("inf")):
            raise ValueError(f"{sid}: invalid initial MQTT sum {first_sum}")
        total_wh = sum(prior.values()) * 1000
        if total_wh <= 0 or first_index + 0.000001 < total_wh:
            raise ValueError(f"{sid}: invalid historical energy / meter index")
        # An inactive tariff can have gaps; cumulative state must remain
        # unchanged across those hours. The first index is a boundary anchor,
        # not independent proof of its sampling time.
        cumulative = 0.0
        rows = []
        for t, kwh in sorted(prior.items()):
            cumulative += kwh * 1000
            rows.append(StatisticData(start=t,
                       state=first_index-total_wh+cumulative,
                       sum=first_sum+cumulative))
        # Recorder's metadata for native sensors must be preserved exactly.
        metadata = await get_instance(hass).async_add_executor_job(
            partial(rs.get_metadata, hass, statistic_ids={sid}))
        item = metadata.get(sid)
        if item is None:
            raise ValueError(f"{sid}: native metadata missing")
        # Recorder get_metadata returns (metadata_id, StatisticMetaData).
        # Validate the actual metadata, not the tuple wrapper.
        meta = item[1] if isinstance(item, tuple) else item
        def attr(name, default=None):
            return meta.get(name, default) if isinstance(meta, dict) else getattr(meta, name, default)
        if attr("source") != "recorder" or not attr("has_sum") or attr("unit_of_measurement") != "Wh":
            raise ValueError(f"{sid}: native metadata incompatible")
        native_meta = StatisticMetaData(has_mean=False, has_sum=True,
                         name=attr("name"), source="recorder", statistic_id=sid,
                         unit_class=attr("unit_class"), unit_of_measurement="Wh")
        prepared.append((sid, boundary, total_wh, native_meta, rows))
        result.append({"tariff": label, "statistic_id": sid,
                       "status": "ready", "hours": len(rows),
                       "historical_wh": round(total_wh, 6),
                       "first_native_hour_utc": boundary.isoformat(),
                       "first_native_sum_wh": first_sum,
                       "expected_first_native_sum_after_wh": round(first_sum+total_wh, 6),
                       "excluded_rest_hours_after_boundary": len(overlap)})
    summary = {"dry_run": not confirm_write, "native_modified": False,
               "days_loaded": days, "tariffs": result,
               "tariffs_ready": len(prepared),
               "historical_wh_total": round(sum(p[2] for p in prepared), 6),
               "include_injection": include_injection, "include_consumption": include_consumption}
    if not confirm_write:
        return summary
    if not prepared:
        return {**summary, "message": "Nothing to import"}
    # Queue all native baseline shifts first, then all historical inserts.
    # Recorder operations are asynchronous and NOT atomic; do not retry until
    # the queued changes have been checked for persistence.
    for sid, boundary, total, meta, rows in prepared:
        get_instance(hass).async_adjust_statistics(sid, boundary, total, "Wh")
        rs.async_import_statistics(hass, meta, rows)
    return {**summary, "dry_run": False, "native_modified": "queued",
            "written": True,
            "message": "Native tariff migration queued. Do not repeat until Recorder has processed the queue."}
