const API_BASE_URL = 'http://localhost:8000';

const ensureArray = (value) => (Array.isArray(value) ? value : []);
const hasText = (value) => typeof value === 'string' && value.trim().length > 0;
const hasObjectKeys = (value) => Boolean(value) && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length > 0;

const normalizeAdvice = (advice, fallbackTactics = []) => {
    const text = typeof advice === 'string' ? advice : advice?.text;
    const fallbackAction = fallbackTactics[0]?.recommended_action || 'Prepare for the next shot.';

    return {
        text: text || 'Stay balanced and prepare early.',
        headline: advice?.headline || 'Stay composed',
        focus: advice?.focus || 'Recovery',
        next_step: advice?.next_step || fallbackAction,
        confidence_label: advice?.confidence_label || fallbackTactics[0]?.confidence_label || 'medium',
        source: advice?.source || 'fallback',
    };
};

const normalizeTactics = (tactics = []) =>
    tactics.map((tactic, index) => {
        const name =
            tactic?.name
            || tactic?.metadata?.name
            || tactic?.content
            || `Tactic ${index + 1}`;

        return {
            ...tactic,
            name,
            content: tactic?.content || name,
            score: tactic?.score || 0,
            semantic_score: tactic?.semantic_score || 0,
            bayesian_score: tactic?.bayesian_score || 0,
            context_score: tactic?.context_score || 0,
            quality_weight: tactic?.quality_weight || 1,
            expected_win_rate: tactic?.expected_win_rate || 50,
            confidence_label: tactic?.confidence_label || 'medium',
            recommended_action: tactic?.recommended_action || tactic?.content || name,
            reason: tactic?.reason || '',
            why_this_tactic: tactic?.why_this_tactic || '',
            risk_note: tactic?.risk_note || '',
            rerank_score: tactic?.rerank_score || tactic?.score || 0,
            continuity_score: tactic?.continuity_score || 0,
            coverage_score: tactic?.coverage_score || 0,
            volatility_guard: tactic?.volatility_guard || 0,
            novelty_bonus: tactic?.novelty_bonus || 0,
            rank_reason: tactic?.rank_reason || '',
            frontier_hint: tactic?.frontier_hint || '',
            evolution_replay: tactic?.evolution_replay || {},
        };
    });

const normalizeSequenceContext = (sequenceContext = {}) => {
    const recentTactics = ensureArray(sequenceContext?.recent_tactics).map((snapshot, index) => ({
        rally_index: snapshot?.rally_index ?? index + 1,
        name: snapshot?.name || `Tactic ${index + 1}`,
        tactic_id: snapshot?.tactic_id || 'unknown',
        style_family: snapshot?.style_family || 'balanced',
        phase_preference: snapshot?.phase_preference || 'neutral',
        risk_level: snapshot?.risk_level || 'medium',
        score: snapshot?.score ?? 0,
    }));
    const tacticTransitions = ensureArray(sequenceContext?.tactic_transitions).map((transition) => ({
        from: transition?.from || 'Unknown',
        to: transition?.to || 'Unknown',
        style_shift: transition?.style_shift || 'balanced -> balanced',
    }));
    const adaptationSignals = ensureArray(sequenceContext?.adaptation_signals);
    const playerAdjustmentSignals = ensureArray(sequenceContext?.player_adjustment_signals);
    const sequenceTags = ensureArray(sequenceContext?.sequence_tags);

    return {
        match_type: sequenceContext?.match_type || 'singles',
        window_size: sequenceContext?.window_size || 0,
        recent_events: ensureArray(sequenceContext?.recent_events),
        recent_results: ensureArray(sequenceContext?.recent_results),
        recent_pressures: ensureArray(sequenceContext?.recent_pressures),
        recent_phases: ensureArray(sequenceContext?.recent_phases),
        recent_tactics: recentTactics,
        event_distribution: sequenceContext?.event_distribution || {},
        tactic_distribution: sequenceContext?.tactic_distribution || {},
        style_distribution: sequenceContext?.style_distribution || {},
        tactic_transitions: tacticTransitions,
        streak_context: sequenceContext?.streak_context || {
            state: 'neutral',
            length: 0,
            last_result: 'UNKNOWN',
        },
        pressure_swing: sequenceContext?.pressure_swing || {
            label: 'steady',
            delta: 0,
            mean_pressure: 0,
            volatility: 0,
        },
        adaptation_signals: adaptationSignals,
        player_adjustment_signals: playerAdjustmentSignals,
        sequence_tags: sequenceTags,
        preferred_style_family: sequenceContext?.preferred_style_family || 'balanced',
        continuity_anchor: sequenceContext?.continuity_anchor || {},
        adaptation_score: sequenceContext?.adaptation_score ?? 0,
        memory_summary: sequenceContext?.memory_summary || '',
        retrieval_context: sequenceContext?.retrieval_context || {},
        has_content: Boolean(
            hasText(sequenceContext?.memory_summary)
            || recentTactics.length > 0
            || tacticTransitions.length > 0
            || adaptationSignals.length > 0
            || playerAdjustmentSignals.length > 0
            || sequenceTags.length > 0
            || Number(sequenceContext?.adaptation_score) > 0
            || hasObjectKeys(sequenceContext?.continuity_anchor)
        ),
    };
};

const normalizeDuelProjection = (duelProjection = {}) => {
    const counterTactics = ensureArray(duelProjection?.counter_tactics).map((counter, index) => ({
        name: counter?.name || `Counter ${index + 1}`,
        family: counter?.family || 'balanced',
        fit_score: counter?.fit_score ?? 0,
        reason: counter?.reason || 'No counter explanation is available.',
    }));
    const exchangeScript = ensureArray(duelProjection?.exchange_script);

    return {
        primary_plan: duelProjection?.primary_plan || 'Neutral reset',
        likely_response: duelProjection?.likely_response || '',
        counter_window: duelProjection?.counter_window || '',
        duel_risk: duelProjection?.duel_risk ?? 0,
        duel_risk_label: duelProjection?.duel_risk_label || 'low',
        counter_tactics: counterTactics,
        exchange_script: exchangeScript,
        duel_explanation: duelProjection?.duel_explanation || '',
        pressure_gate: duelProjection?.pressure_gate || '',
        has_content: Boolean(
            hasText(duelProjection?.likely_response)
            || hasText(duelProjection?.duel_explanation)
            || hasText(duelProjection?.pressure_gate)
            || hasText(duelProjection?.primary_plan)
            || hasText(duelProjection?.counter_window)
            || counterTactics.length > 0
            || exchangeScript.length > 0
            || Number(duelProjection?.duel_risk) > 0
        ),
    };
};

const normalizeTrainingPlan = (trainingPlan = {}) => {
    const blocks = ensureArray(trainingPlan?.blocks).map((block, index) => ({
        label: block?.label || `Block ${index + 1}`,
        duration_min: block?.duration_min ?? 0,
        intensity: block?.intensity || 'medium',
        goal: block?.goal || '',
    }));

    return {
        theme: trainingPlan?.theme || trainingPlan?.match_theme || 'Adaptive training block',
        priority: trainingPlan?.priority || 'pattern-reinforcement',
        micro_goal: trainingPlan?.micro_goal || '',
        guardrail: trainingPlan?.guardrail || '',
        focus_queue: ensureArray(trainingPlan?.focus_queue),
        phase_distribution: ensureArray(trainingPlan?.phase_distribution),
        blocks,
        has_content: Boolean(
            hasText(trainingPlan?.theme)
            || hasText(trainingPlan?.match_theme)
            || hasText(trainingPlan?.micro_goal)
            || hasText(trainingPlan?.guardrail)
            || ensureArray(trainingPlan?.focus_queue).length > 0
            || ensureArray(trainingPlan?.phase_distribution).length > 0
            || blocks.length > 0
        ),
    };
};

const normalizeReplayStory = (replayStory = {}) => {
    const turningPoints = ensureArray(replayStory?.turning_points);
    const adaptationCycles = ensureArray(replayStory?.adaptation_cycles);
    const criticalRallies = ensureArray(replayStory?.critical_rallies);
    const storylineCards = ensureArray(replayStory?.storyline_cards);
    const timelineDigest = ensureArray(replayStory?.timeline_digest);

    return {
        opening_phase: replayStory?.opening_phase || {},
        turning_points: turningPoints,
        adaptation_cycles: adaptationCycles,
        critical_rallies: criticalRallies,
        closing_state: replayStory?.closing_state || {},
        storyline_cards: storylineCards,
        timeline_digest: timelineDigest,
        replay_summary: replayStory?.replay_summary || '',
        has_content: Boolean(
            hasText(replayStory?.replay_summary)
            || turningPoints.length > 0
            || adaptationCycles.length > 0
            || criticalRallies.length > 0
            || storylineCards.length > 0
            || timelineDigest.length > 0
            || hasObjectKeys(replayStory?.opening_phase)
            || hasObjectKeys(replayStory?.closing_state)
        ),
    };
};

const normalizeDiagnostics = (diagnostics = {}) => ({
    warnings: diagnostics?.warnings || [],
    pipeline: diagnostics?.pipeline || {},
    motion_feedback: diagnostics?.motion_feedback || 'Unavailable',
    trajectory_points: diagnostics?.trajectory_points || 0,
    analysis_quality: diagnostics?.analysis_quality || 'medium',
    retrieval_summary: diagnostics?.retrieval_summary || {},
    physics_profile: diagnostics?.physics_profile || {},
    tracker_diagnostics: diagnostics?.tracker_diagnostics || {},
    motion_profile: diagnostics?.motion_profile || {},
    rally_quality: diagnostics?.rally_quality || {},
    confidence_report: diagnostics?.confidence_report || {},
    referee_audit: diagnostics?.referee_audit || {},
    sequence_context: normalizeSequenceContext(diagnostics?.sequence_context),
    duel_projection: normalizeDuelProjection(diagnostics?.duel_projection),
    policy_update: diagnostics?.policy_update || {},
});

const normalizeSummary = (summary = {}) => ({
    headline: summary?.headline || 'Rally captured',
    verdict: summary?.verdict || 'UNKNOWN',
    confidence_label: summary?.confidence_label || 'medium',
    key_takeaway: summary?.key_takeaway || 'Review the recommendation and prepare for the next exchange.',
});

const normalizeReport = (report = {}, diagnostics = {}) => ({
    ...report,
    technical_snapshot: report?.technical_snapshot || {},
    confidence_snapshot: report?.confidence_snapshot || diagnostics?.confidence_report || {},
    tracking_snapshot: report?.tracking_snapshot || diagnostics?.tracker_diagnostics || {},
    referee_snapshot: report?.referee_snapshot || diagnostics?.referee_audit || {},
    sequence_snapshot: report?.sequence_snapshot || diagnostics?.sequence_context || {},
    duel_snapshot: normalizeDuelProjection(report?.duel_snapshot || diagnostics?.duel_projection),
    tactic_snapshot: report?.tactic_snapshot || {},
    training_plan: normalizeTrainingPlan(report?.training_plan),
    replay_story: normalizeReplayStory(report?.replay_story),
    coach_takeaway: report?.coach_takeaway || 'Focus on stable execution in the next exchange.',
});

const buildFallbackReplayStory = (result, diagnostics, report) => {
    const sequenceContext = diagnostics?.sequence_context || {};
    const duelProjection = diagnostics?.duel_projection || {};
    const topTactic = result?.tactics?.[0]?.name || report?.top_tactic || 'Neutral reset';
    const eventName = result?.physics?.event || 'Rally';
    const verdict = result?.auto_result || result?.summary?.verdict || 'UNKNOWN';

    return normalizeReplayStory({
        opening_phase: {
            headline: 'Single rally replay',
            events: [eventName],
            tactics: [topTactic],
            average_pressure: result?.physics?.pressure_index ?? 0,
            summary: `This replay centers on ${eventName} with ${topTactic} as the main tactical anchor.`,
        },
        turning_points: duelProjection?.duel_explanation
            ? [
                {
                    rally_index: 1,
                    trigger: duelProjection.duel_explanation,
                    summary: result?.summary?.headline || 'Rally shift',
                },
            ]
            : [],
        adaptation_cycles: ensureArray(sequenceContext?.tactic_transitions).length > 0
            ? ensureArray(sequenceContext?.tactic_transitions).map((transition) => ({
                from: transition?.from || 'Unknown',
                to: transition?.to || 'Unknown',
                style_shift: transition?.style_shift || 'balanced -> balanced',
                summary: `The tactical read shifted from ${transition?.from || 'Unknown'} to ${transition?.to || 'Unknown'}.`,
            }))
            : [
                {
                    from: 'Initial read',
                    to: topTactic,
                    style_shift: 'single-anchor',
                    summary: report?.coach_takeaway || 'The clip resolves around one main tactical anchor.',
                },
            ],
        critical_rallies: [
            {
                rally_index: 1,
                score: result?.auto_reward ?? 0,
                headline: result?.summary?.headline || 'Critical rally',
                takeaway: result?.summary?.key_takeaway || report?.coach_takeaway || '',
            },
        ],
        closing_state: {
            last_rally_index: 1,
            verdict,
            tactic_anchor: topTactic,
            momentum_state: sequenceContext?.streak_context?.state || 'neutral',
            dominant_duel: duelProjection?.primary_plan || topTactic,
            summary: `The replay closes on a ${verdict.toLowerCase()} verdict with ${topTactic} as the tactical anchor.`,
        },
        storyline_cards: [
            {
                stage: 'opening',
                title: eventName,
                body: sequenceContext?.memory_summary || result?.summary?.key_takeaway || 'Replay summary unavailable.',
            },
            {
                stage: 'duel',
                title: duelProjection?.primary_plan || topTactic,
                body: duelProjection?.likely_response || 'No duel response was generated.',
            },
            {
                stage: 'closing',
                title: 'Coach takeaway',
                body: report?.coach_takeaway || result?.summary?.key_takeaway || 'Review the exchange and prepare the next response.',
            },
        ],
        timeline_digest: [
            {
                rally_index: 1,
                event: eventName,
                verdict,
                top_tactic: topTactic,
                pressure: result?.physics?.pressure_index ?? 0,
            },
        ],
        replay_summary: report?.coach_takeaway || result?.summary?.key_takeaway || 'Replay story is unavailable for this clip.',
    });
};

const normalizeAnalysisResult = (result) => {
    const diagnostics = normalizeDiagnostics(result?.diagnostics);
    const report = normalizeReport(result?.report, diagnostics);
    const tactics = normalizeTactics(result?.tactics).map((tactic, index) => {
        if (index !== 0) {
            return tactic;
        }

        const reportTacticSnapshot = report?.tactic_snapshot || {};

        return {
            ...tactic,
            why_this_tactic: tactic?.why_this_tactic || reportTacticSnapshot?.why_this_tactic || '',
            risk_note: tactic?.risk_note || reportTacticSnapshot?.risk_note || '',
            rank_reason: tactic?.rank_reason || reportTacticSnapshot?.rank_reason || '',
            frontier_hint: tactic?.frontier_hint || reportTacticSnapshot?.frontier_hint || '',
            evolution_replay: hasObjectKeys(tactic?.evolution_replay)
                ? tactic.evolution_replay
                : (reportTacticSnapshot?.evolution_replay || {}),
        };
    });
    const replayStory = normalizeReplayStory(
        result?.replay_story
        || result?.match_summary?.replay_story
        || report?.replay_story
        || buildFallbackReplayStory(
            {
                ...result,
                tactics,
            },
            diagnostics,
            report,
        ),
    );

    return {
        ...result,
        match_type: result?.match_type || diagnostics?.sequence_context?.match_type || 'singles',
        advice: normalizeAdvice(result?.advice, tactics),
        tactics,
        summary: normalizeSummary(result?.summary),
        diagnostics,
        report,
        replay_story: replayStory,
        physics: {
            ...result?.physics,
            description: result?.physics?.description || 'No analysis details available.',
            referee_confidence: result?.physics?.referee_confidence ?? 0.72,
            trajectory_quality: result?.physics?.trajectory_quality ?? 0.78,
            referee_reason: result?.physics?.referee_reason || 'Referee explanation is unavailable.',
        },
    };
};

const createDebugResponse = (videoUrl, matchType) => ({
    videoUrl,
    physics: {
        event: 'Power Smash',
        max_speed_kmh: 235,
        duration: 4.5,
        description: `Mode: ${matchType === 'doubles' ? 'Doubles' : 'Singles'}. Event: Power Smash. Max shuttle speed 235 km/h. Verdict: point won.`,
        trajectory_quality: 0.84,
        referee_confidence: 0.87,
        referee_reason: 'Last hitter was inferred as the user with a stable downward finish, and the landing point was comfortably inside the court.',
        court_context: 'rear_channel',
        attack_phase: 'advantage',
        tempo_profile: 'fast',
        pressure_index: 0.47,
        rally_state: {
            trajectory_quality: 0.84,
            landing_confidence: 0.9,
            direction_consistency: 0.82,
            speed_profile: {
                mean_speed_kmh: 118.4,
                max_speed_kmh: 235,
                end_speed_kmh: 58.2,
            },
            court_context: 'rear_channel',
        },
    },
    advice: {
        text: 'Keep leaning into the counter block and recover forward immediately after contact.',
        headline: 'Attack the reply',
        focus: 'Transition speed',
        next_step: 'Block soft to the forecourt, then step in aggressively.',
        confidence_label: 'high',
        source: 'debug',
    },
    tactics: [
        {
            name: 'Counter Block',
            content: 'Use a soft backhand block to pull the attacker forward after a heavy smash.',
            metadata: {
                tactic_id: 'T001',
                name: 'Counter Block',
                alpha: 5,
                beta: 1,
                style_family: 'absorb-and-redirect',
                phase_preference: 'under_pressure',
                risk_level: 'medium',
            },
            score: 0.91,
            semantic_score: 0.83,
            bayesian_score: 0.95,
            context_score: 0.88,
            quality_weight: 0.97,
            expected_win_rate: 83.3,
            confidence_label: 'high',
            recommended_action: 'Use a soft backhand block to pull the attacker forward after a heavy smash.',
            reason: 'Counter Block is the top recommendation because it fits a power-smash scenario at 235.0 km/h and carries a strong expected win rate.',
            why_this_tactic: 'This is the clearest match for a heavy rear-court attack because it converts the opponent\'s pace into a front-court pressure opportunity.',
            risk_note: 'The shuttle pace is very high here, so the block only works if your racket face stays soft and stable at contact.',
            rerank_score: 0.94,
            continuity_score: 0.89,
            coverage_score: 0.84,
            rank_reason: 'Counter Block stayed on top because continuity and volatility guard both remained strong through the sequence.',
            frontier_hint: 'This branch is stable enough to keep reinforcing in under-pressure exchanges.',
            evolution_replay: {
                development_stage: 'refine',
                policy_mode: 'exploit',
                replay_score: 0.94,
                risk_axis: 'medium',
                training_block: 'pressure absorb + counter release',
                why_now: 'Counter Block is relevant now because it preserved strong rank value while the pressure script was easing.',
                upgrade_path: [
                    'Rehearse Counter Block entries from under-pressure situations.',
                    'Track whether the first attacking touch creates space or panic.',
                    'Reinforce the most repeatable variation and trim noisy branches.',
                ],
            },
        },
        {
            name: 'Deep Lift Reset',
            content: 'Lift high and deep to the rear court corners to reset the rally and buy recovery time.',
            metadata: {
                tactic_id: 'T002',
                name: 'Deep Lift Reset',
                alpha: 3,
                beta: 2,
                style_family: 'reset-and-rebuild',
                phase_preference: 'neutral',
                risk_level: 'low',
            },
            score: 0.74,
            semantic_score: 0.71,
            bayesian_score: 0.69,
            context_score: 0.72,
            quality_weight: 0.94,
            expected_win_rate: 60,
            confidence_label: 'medium',
            recommended_action: 'Lift high and deep to the rear court corners to reset the rally and buy recovery time.',
            reason: 'Deep Lift Reset remains viable because it slows the exchange and rebuilds court balance.',
            why_this_tactic: 'It is a safer secondary option when you cannot control the block cleanly and need extra recovery time.',
            risk_note: 'If the lift sits short, you may give the attacker another full-power ball.',
            rerank_score: 0.76,
            continuity_score: 0.61,
            coverage_score: 0.7,
            rank_reason: 'Deep Lift Reset remains on the board as a lower-risk fallback when the duel gets rushed.',
            frontier_hint: 'Keep this lane alive as a secondary variation when the block timing is late.',
            evolution_replay: {
                development_stage: 'stabilize',
                policy_mode: 'balanced',
                replay_score: 0.71,
                risk_axis: 'low',
                training_block: 'tempo control and shape preservation',
                why_now: 'Deep Lift Reset stays relevant whenever the exchange cannot be softened cleanly at the net.',
                upgrade_path: [
                    'Rehearse the high lift from defensive entries.',
                    'Track whether the reset buys enough recovery time.',
                    'Use it as the backup branch when the primary duel becomes unstable.',
                ],
            },
        },
    ],
    summary: {
        headline: 'Winning pattern detected',
        verdict: 'WIN',
        confidence_label: 'high',
        key_takeaway: 'Primary tactical direction: Counter Block. Focus on transition speed in the next exchange.',
    },
    diagnostics: {
        warnings: [],
        pipeline: {
            court_detection: 'ok',
            tracking: 'ok',
            pose: 'ok',
            physics: 'ok',
            retrieval: 'ok',
            coach: 'ok',
        },
        motion_feedback: 'Base control is solid, but there is room for a lower defensive stance. | Contact point is well extended with strong striking structure.',
        trajectory_points: 18,
        analysis_quality: 'high',
        sequence_context: {
            match_type: matchType,
            window_size: 3,
            recent_events: ['Steep Smash', 'Drive Exchange', 'Power Smash'],
            recent_results: ['LOSS', 'WIN', 'WIN'],
            recent_pressures: [0.72, 0.58, 0.47],
            recent_phases: ['under_pressure', 'transition', 'advantage'],
            recent_tactics: [
                {
                    rally_index: 1,
                    name: 'Straight Relief Clear',
                    tactic_id: 'T004',
                    style_family: 'reset-and-rebuild',
                    phase_preference: 'under_pressure',
                    risk_level: 'low',
                    score: 0.69,
                },
                {
                    rally_index: 2,
                    name: 'Body Drive Jam',
                    tactic_id: 'T006',
                    style_family: 'compression-attack',
                    phase_preference: 'neutral',
                    risk_level: 'medium',
                    score: 0.81,
                },
                {
                    rally_index: 3,
                    name: 'Counter Block',
                    tactic_id: 'T001',
                    style_family: 'absorb-and-redirect',
                    phase_preference: 'under_pressure',
                    risk_level: 'medium',
                    score: 0.91,
                },
            ],
            tactic_transitions: [
                {
                    from: 'Straight Relief Clear',
                    to: 'Body Drive Jam',
                    style_shift: 'reset-and-rebuild -> compression-attack',
                },
                {
                    from: 'Body Drive Jam',
                    to: 'Counter Block',
                    style_shift: 'compression-attack -> absorb-and-redirect',
                },
            ],
            streak_context: {
                state: 'surging',
                length: 2,
                last_result: 'WIN',
            },
            pressure_swing: {
                label: 'releasing-pressure',
                delta: -0.25,
                mean_pressure: 0.59,
                volatility: 0.1,
            },
            adaptation_signals: [
                'The recent sequence keeps returning to smash-pressure patterns.',
                'Counter Block has been revisited repeatedly as the preferred answer.',
            ],
            player_adjustment_signals: [
                'Attack phase shifted from under pressure to advantage.',
                'Pressure load dropped after the latest tactical adjustment.',
            ],
            sequence_tags: ['releasing-pressure', 'surging-streak', 'adaptation-live'],
            preferred_style_family: 'absorb-and-redirect',
            continuity_anchor: {
                name: 'Counter Block',
                style_family: 'absorb-and-redirect',
            },
            adaptation_score: 0.68,
            memory_summary: 'Sequence memory sees pressure releasing across the last few exchanges, with Counter Block becoming the most stable tactical anchor.',
        },
        duel_projection: {
            primary_plan: 'Counter Block',
            likely_response: 'The opponent is likely to shorten the exchange and attack the first loose reply.',
            counter_window: 'first-two-shots',
            duel_risk: 0.58,
            duel_risk_label: 'medium',
            counter_tactics: [
                {
                    name: 'Body Drive Jam',
                    family: 'compression-attack',
                    fit_score: 0.81,
                    reason: 'Body Drive Jam fits transition exchanges and punishes a soft forecourt block if the opponent crowds early.',
                },
                {
                    name: 'Midcourt Intercept Swipe',
                    family: 'interception',
                    fit_score: 0.77,
                    reason: 'Midcourt Intercept Swipe becomes dangerous if the next ball stays flat and loose through midcourt.',
                },
            ],
            exchange_script: [
                'Open with Counter Block from a stabilizing base.',
                'The opponent is likely to attack the first loose reply.',
                'If the exchange turns, Body Drive Jam is the cleanest counter lane.',
            ],
            duel_explanation: 'Counter Block enters a medium-risk duel because the pressure is easing, but the opponent still has a live fast-exchange counter if the block sits up.',
            pressure_gate: 'Take the duel only when the base remains balanced after the first contact.',
        },
        policy_update: {
            weighted_increment: 0.87,
            quality_weight: 0.91,
            confidence_weight: 0.96,
            exploration_guard: 0.85,
            adaptation_level: 'strong',
            policy_update_reason: 'Updated alpha using strong trajectory quality, high referee confidence, and high retrieval confidence.',
            reward_components: {
                raw_reward: 10,
                trajectory_quality: 0.84,
                referee_confidence: 0.87,
                retrieval_confidence: 0.91,
            },
        },
    },
    report: {
        headline: 'Winning pattern detected',
        verdict: 'WIN',
        top_tactic: 'Counter Block',
        technical_snapshot: {
            event: 'Power Smash',
            pressure_index: 0.47,
            attack_phase: 'advantage',
            tempo_profile: 'fast',
        },
        confidence_snapshot: {
            calibrated_confidence: 0.89,
            volatility: 0.18,
            caution_level: 'low',
        },
        tracking_snapshot: {
            signal_integrity: 0.92,
            repaired_points: 1,
            spike_count: 0,
        },
        referee_snapshot: {
            audit_level: 'clean',
            verdict_stability: 0.86,
            recommended_action: 'The power smash verdict is stable enough to use as a training signal.',
        },
        sequence_snapshot: {
            memory_summary: 'Sequence memory sees pressure releasing across the last few exchanges, with Counter Block becoming the most stable tactical anchor.',
            sequence_tags: ['releasing-pressure', 'surging-streak', 'adaptation-live'],
            streak_context: {
                state: 'surging',
                length: 2,
                last_result: 'WIN',
            },
        },
        duel_snapshot: {
            primary_plan: 'Counter Block',
            likely_response: 'The opponent is likely to shorten the exchange and attack the first loose reply.',
            counter_window: 'first-two-shots',
            duel_risk: 0.58,
            duel_risk_label: 'medium',
            counter_tactics: [
                {
                    name: 'Body Drive Jam',
                    family: 'compression-attack',
                    fit_score: 0.81,
                    reason: 'Body Drive Jam fits transition exchanges and punishes a soft forecourt block if the opponent crowds early.',
                },
            ],
            exchange_script: [
                'Open with Counter Block from a stabilizing base.',
                'The opponent is likely to attack the first loose reply.',
                'If the exchange turns, Body Drive Jam is the cleanest counter lane.',
            ],
            duel_explanation: 'Counter Block enters a medium-risk duel because the pressure is easing, but the opponent still has a live fast-exchange counter if the block sits up.',
            pressure_gate: 'Take the duel only when the base remains balanced after the first contact.',
        },
        tactic_snapshot: {
            why_this_tactic: 'Counter Block converts the opponent\'s pace into a forecourt recovery problem.',
            risk_note: 'Keep the racket face soft. A floating block immediately reopens the attack.',
            rank_reason: 'Counter Block stayed on top because continuity and volatility guard both remained strong through the sequence.',
            frontier_hint: 'This branch is stable enough to keep reinforcing in under-pressure exchanges.',
            evolution_replay: {
                development_stage: 'refine',
                policy_mode: 'exploit',
                replay_score: 0.94,
                risk_axis: 'medium',
                training_block: 'pressure absorb + counter release',
                why_now: 'Counter Block is relevant now because it preserved strong rank value while the pressure script was easing.',
                upgrade_path: [
                    'Rehearse Counter Block entries from under-pressure situations.',
                    'Track whether the first attacking touch creates space or panic.',
                    'Reinforce the most repeatable variation and trim noisy branches.',
                ],
            },
        },
        training_plan: {
            theme: 'Under Pressure Execution Around Counter Block',
            priority: 'pattern-reinforcement',
            micro_goal: 'Preserve shape first, then apply the soft forecourt block into forward recovery.',
            guardrail: 'Only take the duel when the base remains balanced after contact.',
            blocks: [
                {
                    label: 'Shadow Rehearsal',
                    duration_min: 8,
                    intensity: 'low',
                    goal: 'Pattern the entry into Counter Block without rushing the racket face.',
                },
                {
                    label: 'Constraint Feed',
                    duration_min: 12,
                    intensity: 'medium',
                    goal: 'Trigger the block only after a stable first defensive read.',
                },
            ],
        },
        coach_takeaway: 'Use the replay to notice how the pressure script softened once the block stopped feeding the attacker.',
    },
    replay_story: {
        opening_phase: {
            headline: 'Opening phase',
            events: ['Steep Smash', 'Drive Exchange'],
            tactics: ['Straight Relief Clear', 'Body Drive Jam'],
            average_pressure: 0.65,
            summary: 'The clip opens with defensive stress, then shifts into a flatter tempo before the block pattern stabilizes the rally.',
        },
        turning_points: [
            {
                rally_index: 2,
                trigger: 'The tactical anchor shifted from Straight Relief Clear to Body Drive Jam.',
                summary: 'Tempo flipped into transition play.',
            },
            {
                rally_index: 3,
                trigger: 'The result flipped from LOSS to WIN, shifting match momentum.',
                summary: 'Counter Block converted defense into initiative.',
            },
        ],
        adaptation_cycles: [
            {
                from: 'Straight Relief Clear',
                to: 'Body Drive Jam',
                style_shift: 'reset-and-rebuild -> compression-attack',
                summary: 'The exchange moved from survival mode into a more assertive transition lane.',
            },
            {
                from: 'Body Drive Jam',
                to: 'Counter Block',
                style_shift: 'compression-attack -> absorb-and-redirect',
                summary: 'The final adaptation chose control over speed and turned pressure back onto the opponent.',
            },
        ],
        critical_rallies: [
            {
                rally_index: 3,
                score: 0.84,
                headline: 'Winning pattern detected',
                takeaway: 'Primary tactical direction: Counter Block. Focus on transition speed in the next exchange.',
            },
        ],
        closing_state: {
            last_rally_index: 3,
            verdict: 'WIN',
            tactic_anchor: 'Counter Block',
            momentum_state: 'surging',
            dominant_duel: 'Counter Block -> The opponent is likely to shorten the exchange and attack the first loose reply.',
            summary: 'The replay closes with Counter Block as the latest anchor and a surging momentum state.',
        },
        storyline_cards: [
            {
                stage: 'opening',
                title: 'Under pressure start',
                body: 'The opening exchange was defensive and forced a reset-first mindset.',
            },
            {
                stage: 'turn',
                title: 'Transition unlock',
                body: 'Body Drive Jam reopened tempo and created a more active recovery shape.',
            },
            {
                stage: 'adapt',
                title: 'Counter Block anchor',
                body: 'The final adaptation used control to turn the smash pattern back against the opponent.',
            },
            {
                stage: 'closing',
                title: 'Replay takeaway',
                body: 'The point was won once the recovery path stayed organized through the block.',
            },
        ],
        timeline_digest: [
            {
                rally_index: 1,
                event: 'Steep Smash',
                verdict: 'LOSS',
                top_tactic: 'Straight Relief Clear',
                pressure: 0.72,
            },
            {
                rally_index: 2,
                event: 'Drive Exchange',
                verdict: 'WIN',
                top_tactic: 'Body Drive Jam',
                pressure: 0.58,
            },
            {
                rally_index: 3,
                event: 'Power Smash',
                verdict: 'WIN',
                top_tactic: 'Counter Block',
                pressure: 0.47,
            },
        ],
        replay_summary: 'The replay starts under pressure, unlocks through a faster transition exchange, and closes once Counter Block becomes the stable tactical answer.',
    },
    match_type: matchType,
    auto_result: 'WIN',
    auto_reward: 10,
});

export const api = {
    async uploadVideo(videoFile, options = {}) {
        const { isDebug = false, matchType = 'singles' } = options;

        if (isDebug) {
            const debugVideoUrl = videoFile ? URL.createObjectURL(videoFile) : '/samples/after.mp4';

            return new Promise((resolve) => {
                window.setTimeout(() => {
                    resolve(normalizeAnalysisResult(createDebugResponse(debugVideoUrl, matchType)));
                }, 1200);
            });
        }

        if (!videoFile) {
            throw new Error('Please select or record a clip before starting analysis.');
        }

        const formData = new FormData();
        formData.append('file', videoFile);
        formData.append('match_type', matchType);

        try {
            const localVideoUrl = URL.createObjectURL(videoFile);
            const response = await fetch(`${API_BASE_URL}/analyze_rally`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Analysis failed.');
            }

            const data = await response.json();

            return normalizeAnalysisResult({
                videoUrl: localVideoUrl,
                ...data,
            });
        } catch (error) {
            console.error('[API] Upload failed:', error);
            throw error;
        }
    },
};
