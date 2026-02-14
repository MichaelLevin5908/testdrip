/**
 * Drip C++ SDK - ML Training Integration Tests
 *
 * Simulates realistic ML training workflows as a Play2Train / glades-ml
 * consumer would use them. Exercises the full Drip API surface:
 *
 *   1.  Multi-epoch training run with per-epoch token metering
 *   2.  Model checkpoint / state-save event tracking
 *   3.  Per-user usage attribution (multiple platform users)
 *   4.  Failed training run (divergence detection)
 *   5.  Multi-model architecture comparison
 *   6.  Incremental run API (startRun → emitEvent → endRun)
 *   7.  Inference / prediction metering (deployed model)
 *   8.  Idempotency / retry safety (duplicate detection)
 *   9.  Hyperparameter sweep (grid search cost comparison)
 *   10. Batch inference job (dataset scoring)
 *
 * Environment variables:
 *   DRIP_API_KEY       - Required
 *   DRIP_API_URL       - Optional (default: production)
 *   TEST_CUSTOMER_ID   - Optional (default: seed-customer-1)
 *
 * Usage:
 *   ./drip-ml-test                # Run all scenarios
 *   ./drip-ml-test --scenario 3   # Run a specific scenario (1-6)
 *   ./drip-ml-test --verbose      # Show extra details
 */

#include <drip/drip.hpp>

#include <iostream>
#include <string>
#include <vector>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <iomanip>
#include <cmath>

// =============================================================================
// ANSI colors
// =============================================================================

static const char* GREEN  = "\033[32m";
static const char* RED    = "\033[31m";
static const char* CYAN   = "\033[36m";
static const char* DIM    = "\033[2m";
static const char* BOLD   = "\033[1m";
static const char* RESET  = "\033[0m";

// =============================================================================
// Types
// =============================================================================

struct ScenarioResult {
    int number;
    std::string name;
    bool success;
    int duration_ms;
    std::string message;
    std::string details;
};

// =============================================================================
// Helpers
// =============================================================================

static std::string env_or(const char* name, const std::string& fallback) {
    const char* val = std::getenv(name);
    if (val && val[0] != '\0') return std::string(val);
    return fallback;
}

static int64_t now_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()
    ).count();
}

static std::string to_string_2f(double v) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(2) << v;
    return ss.str();
}

// =============================================================================
// Scenario 1: Multi-Epoch Training Run
//
// Simulates a glades-ml training session: 5 epochs, each processing a batch
// of tokens. Records the full run with per-epoch events and loss tracking.
// This is the bread-and-butter of how Play2Train would meter training costs.
// =============================================================================

static ScenarioResult scenario_training_run(drip::Client& client,
                                            const std::string& customer_id,
                                            bool verbose) {
    auto start = now_ms();
    try {
        drip::RecordRunParams params;
        params.customer_id = customer_id;
        params.workflow = "glades-training";
        params.status = drip::RUN_COMPLETED;
        params.metadata["model_name"] = "play2train-ffn-v3";
        params.metadata["framework"] = "glades-ml";
        params.metadata["architecture"] = "feed_forward";
        params.metadata["hidden_layers"] = "3";
        params.metadata["learning_rate"] = "0.001";

        // Simulate 5 epochs of training
        int total_tokens = 0;
        double losses[] = {2.31, 1.87, 1.42, 1.08, 0.83};

        for (int epoch = 1; epoch <= 5; ++epoch) {
            int tokens_this_epoch = 2048 * epoch; // increasing dataset
            total_tokens += tokens_this_epoch;

            drip::RecordRunEvent evt;
            evt.event_type = "training.epoch";
            evt.quantity = tokens_this_epoch;
            evt.units = "tokens";
            evt.cost_units = tokens_this_epoch * 0.00001; // $0.01 per 1k tokens
            evt.metadata["epoch"] = std::to_string(epoch);
            evt.metadata["loss"] = to_string_2f(losses[epoch - 1]);
            evt.metadata["batch_size"] = "64";

            std::ostringstream desc;
            desc << "Epoch " << epoch << "/5: " << tokens_this_epoch
                 << " tokens, loss=" << to_string_2f(losses[epoch - 1]);
            evt.description = desc.str();

            params.events.push_back(evt);
        }

        // Final summary event
        drip::RecordRunEvent summary;
        summary.event_type = "training.complete";
        summary.quantity = total_tokens;
        summary.units = "tokens";
        summary.description = "Training complete: 5 epochs, final loss=0.83";
        summary.metadata["total_epochs"] = "5";
        summary.metadata["final_loss"] = "0.83";
        summary.metadata["total_tokens"] = std::to_string(total_tokens);
        params.events.push_back(summary);

        auto result = client.recordRun(params);
        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << result.summary << " | " << result.events.created << " events, "
            << total_tokens << " tokens tracked";

        std::string det;
        if (verbose) {
            std::ostringstream ds;
            ds << "Run ID: " << result.run.id
               << ", Workflow: " << result.run.workflow_name
               << ", Cost: " << result.total_cost_units;
            det = ds.str();
        }

        return {1, "Multi-Epoch Training Run", true, dur, msg.str(), det};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {1, "Multi-Epoch Training Run", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 2: Checkpoint / State Save Tracking
//
// Simulates a longer training with periodic checkpoint saves (model state
// serialization). Haskellol mentioned he already does model versioning and
// "in depth state saving and checkpoints." This shows Drip tracking each
// checkpoint event within a training run.
// =============================================================================

static ScenarioResult scenario_checkpoint_tracking(drip::Client& client,
                                                   const std::string& customer_id,
                                                   bool verbose) {
    auto start = now_ms();
    try {
        drip::RecordRunParams params;
        params.customer_id = customer_id;
        params.workflow = "glades-checkpoint-training";
        params.status = drip::RUN_COMPLETED;
        params.metadata["model_name"] = "play2train-ffn-v3.2";
        params.metadata["checkpoint_interval"] = "every_3_epochs";

        // 9 epochs with checkpoints at 3, 6, 9
        for (int epoch = 1; epoch <= 9; ++epoch) {
            // Epoch event
            drip::RecordRunEvent epoch_evt;
            epoch_evt.event_type = "training.epoch";
            epoch_evt.quantity = 4096;
            epoch_evt.units = "tokens";
            epoch_evt.cost_units = 4096 * 0.00001;
            epoch_evt.metadata["epoch"] = std::to_string(epoch);
            double loss = 2.5 * std::exp(-0.15 * epoch);
            epoch_evt.metadata["loss"] = to_string_2f(loss);
            params.events.push_back(epoch_evt);

            // Checkpoint at every 3rd epoch
            if (epoch % 3 == 0) {
                drip::RecordRunEvent ckpt;
                ckpt.event_type = "model.checkpoint";
                ckpt.quantity = 1;
                ckpt.units = "saves";
                ckpt.cost_units = 0.005; // small storage cost per save

                std::ostringstream path;
                path << "checkpoints/ffn-v3.2-epoch" << epoch << ".bin";
                ckpt.metadata["checkpoint_path"] = path.str();
                ckpt.metadata["epoch"] = std::to_string(epoch);
                ckpt.metadata["loss_at_save"] = to_string_2f(loss);
                ckpt.metadata["model_size_mb"] = "24";

                std::ostringstream desc;
                desc << "Checkpoint saved at epoch " << epoch
                     << " (loss=" << to_string_2f(loss) << ")";
                ckpt.description = desc.str();

                params.events.push_back(ckpt);
            }
        }

        auto result = client.recordRun(params);
        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << result.events.created << " events (9 epochs + 3 checkpoints)";

        std::string det;
        if (verbose) {
            std::ostringstream ds;
            ds << "Run ID: " << result.run.id
               << ", Cost: " << result.total_cost_units;
            det = ds.str();
        }

        return {2, "Checkpoint / State Save Tracking", true, dur, msg.str(), det};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {2, "Checkpoint / State Save Tracking", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 3: Per-User Usage Attribution
//
// Play2Train has multiple users. Each user triggers training runs.
// This simulates 3 different platform users each making trackUsage calls,
// showing how Drip attributes costs to individual end-users.
// =============================================================================

static ScenarioResult scenario_per_user_attribution(drip::Client& client,
                                                    const std::string& customer_id,
                                                    bool verbose) {
    auto start = now_ms();
    try {
        // In production, each Play2Train user maps to a Drip customer.
        // For testing, we use the same customer_id but differentiate via metadata.
        struct UserRun {
            const char* username;
            const char* model;
            int tokens;
        };

        UserRun users[] = {
            {"alice_gamer",   "alice-custom-ffn",  3200},
            {"bob_trainer",   "bob-reinforcement", 8500},
            {"carol_researcher", "carol-deep-net", 15000}
        };

        int total_events = 0;
        std::ostringstream detail_ss;

        for (int i = 0; i < 3; ++i) {
            drip::TrackUsageParams params;
            params.customer_id = customer_id;
            params.meter = "ml_training_tokens";
            params.quantity = users[i].tokens;
            params.units = "tokens";
            params.metadata["platform"] = "play2train";
            params.metadata["platform_user"] = users[i].username;
            params.metadata["model_name"] = users[i].model;
            params.metadata["sdk"] = "cpp";

            std::ostringstream desc;
            desc << "Training by " << users[i].username
                 << ": " << users[i].tokens << " tokens on " << users[i].model;
            params.description = desc.str();

            auto result = client.trackUsage(params);
            ++total_events;

            if (verbose) {
                detail_ss << "  " << users[i].username << " -> "
                          << result.usage_event_id << "\n";
            }
        }

        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << total_events << " users metered: alice(3.2k), bob(8.5k), carol(15k) tokens";

        return {3, "Per-User Usage Attribution", true, dur, msg.str(),
                detail_ss.str()};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {3, "Per-User Usage Attribution", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 4: Failed Training Run (Divergence)
//
// Not every training run succeeds. This simulates a run that detects loss
// divergence (NaN/Inf) and records as FAILED with error metadata.
// Shows how Drip tracks failed runs for cost attribution and debugging.
// =============================================================================

static ScenarioResult scenario_failed_training(drip::Client& client,
                                               const std::string& customer_id,
                                               bool verbose) {
    auto start = now_ms();
    try {
        drip::RecordRunParams params;
        params.customer_id = customer_id;
        params.workflow = "glades-training";
        params.status = drip::RUN_FAILED;
        params.error_message = "Training diverged: loss became NaN at epoch 4";
        params.error_code = "DIVERGENCE_DETECTED";
        params.metadata["model_name"] = "experimental-deep-ffn";
        params.metadata["framework"] = "glades-ml";
        params.metadata["learning_rate"] = "0.1"; // too high!

        // 3 good epochs then divergence
        double losses[] = {2.31, 2.45, 5.82};
        for (int epoch = 1; epoch <= 3; ++epoch) {
            drip::RecordRunEvent evt;
            evt.event_type = "training.epoch";
            evt.quantity = 2048;
            evt.units = "tokens";
            evt.cost_units = 2048 * 0.00001;
            evt.metadata["epoch"] = std::to_string(epoch);
            evt.metadata["loss"] = to_string_2f(losses[epoch - 1]);
            params.events.push_back(evt);
        }

        // Divergence event
        drip::RecordRunEvent fail_evt;
        fail_evt.event_type = "training.error";
        fail_evt.quantity = 1;
        fail_evt.description = "Loss diverged to NaN at epoch 4, aborting";
        fail_evt.metadata["last_valid_loss"] = "5.82";
        fail_evt.metadata["epoch"] = "4";
        fail_evt.metadata["cause"] = "learning_rate_too_high";
        params.events.push_back(fail_evt);

        auto result = client.recordRun(params);
        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << "Failed run recorded: " << result.events.created
            << " events (3 epochs + error)";

        std::string det;
        if (verbose) {
            std::ostringstream ds;
            ds << "Run ID: " << result.run.id
               << ", Status: " << drip::run_status_to_string(result.run.status)
               << ", Cost: " << result.total_cost_units;
            det = ds.str();
        }

        return {4, "Failed Training Run (Divergence)", true, dur, msg.str(), det};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {4, "Failed Training Run (Divergence)", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 5: Multi-Model Architecture Comparison
//
// Common ML workflow: train several architectures and compare costs.
// Records 3 training runs with different configs, then tracks a comparison
// summary event. Shows how a platform can compare cost-per-model.
// =============================================================================

static ScenarioResult scenario_model_comparison(drip::Client& client,
                                                const std::string& customer_id,
                                                bool verbose) {
    auto start = now_ms();
    try {
        struct ModelConfig {
            const char* name;
            const char* workflow;
            int layers;
            int tokens_per_epoch;
            int epochs;
            double final_loss;
        };

        ModelConfig models[] = {
            {"ffn-small",  "glades-arch-compare", 2,  1024, 10, 1.21},
            {"ffn-medium", "glades-arch-compare", 4,  2048,  8, 0.87},
            {"ffn-large",  "glades-arch-compare", 8,  4096,  6, 0.64}
        };

        std::ostringstream detail_ss;
        int total_runs = 0;

        for (int m = 0; m < 3; ++m) {
            drip::RecordRunParams params;
            params.customer_id = customer_id;
            params.workflow = models[m].workflow;
            params.status = drip::RUN_COMPLETED;
            params.metadata["model_name"] = models[m].name;
            params.metadata["hidden_layers"] = std::to_string(models[m].layers);
            params.metadata["comparison_group"] = "arch-benchmark-001";

            int total_tokens = 0;
            for (int e = 1; e <= models[m].epochs; ++e) {
                total_tokens += models[m].tokens_per_epoch;

                drip::RecordRunEvent evt;
                evt.event_type = "training.epoch";
                evt.quantity = models[m].tokens_per_epoch;
                evt.units = "tokens";
                evt.cost_units = models[m].tokens_per_epoch * 0.00001;
                evt.metadata["epoch"] = std::to_string(e);
                params.events.push_back(evt);
            }

            // Evaluation event
            drip::RecordRunEvent eval;
            eval.event_type = "training.evaluation";
            eval.quantity = 1;
            eval.description = std::string(models[m].name)
                + ": final_loss=" + to_string_2f(models[m].final_loss);
            eval.metadata["final_loss"] = to_string_2f(models[m].final_loss);
            eval.metadata["total_tokens"] = std::to_string(total_tokens);
            params.events.push_back(eval);

            auto result = client.recordRun(params);
            ++total_runs;

            if (verbose) {
                detail_ss << "  " << models[m].name << ": "
                          << result.events.created << " events, "
                          << total_tokens << " tokens, cost="
                          << result.total_cost_units << "\n";
            }
        }

        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << total_runs << " model architectures compared: "
            << "small(2L), medium(4L), large(8L)";

        return {5, "Multi-Model Architecture Comparison", true, dur,
                msg.str(), detail_ss.str()};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {5, "Multi-Model Architecture Comparison", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 6: Incremental Run API (startRun → emitEvent → endRun)
//
// Uses the granular run lifecycle API instead of recordRun(). This is what
// a real-time training monitor would use: start a run, stream events as
// epochs complete, then close the run. Shows the full run lifecycle.
// =============================================================================

static ScenarioResult scenario_incremental_run(drip::Client& client,
                                               const std::string& customer_id,
                                               bool verbose) {
    auto start = now_ms();
    try {
        // Step 0: Ensure the workflow exists by doing a quick recordRun first.
        // startRun requires an existing workflow ID, while recordRun auto-creates.
        {
            drip::RecordRunParams seed;
            seed.customer_id = customer_id;
            seed.workflow = "glades-realtime-training";
            seed.status = drip::RUN_COMPLETED;

            drip::RecordRunEvent evt;
            evt.event_type = "workflow.init";
            evt.quantity = 1;
            evt.description = "Workflow bootstrap for incremental API test";
            seed.events.push_back(evt);

            client.recordRun(seed);
        }

        // Step 1: Start the run using the now-existing workflow slug
        // We need the workflow ID — get it from a fresh recordRun result
        std::string workflow_id;
        {
            drip::RecordRunParams probe;
            probe.customer_id = customer_id;
            probe.workflow = "glades-realtime-training";
            probe.status = drip::RUN_COMPLETED;

            drip::RecordRunEvent evt;
            evt.event_type = "workflow.probe";
            evt.quantity = 1;
            probe.events.push_back(evt);

            auto probe_result = client.recordRun(probe);
            workflow_id = probe_result.run.workflow_id;
        }

        drip::StartRunParams start_params;
        start_params.customer_id = customer_id;
        start_params.workflow_id = workflow_id;
        start_params.metadata["model_name"] = "play2train-live-v1";
        start_params.metadata["framework"] = "glades-ml";
        start_params.metadata["mode"] = "incremental";

        auto run = client.startRun(start_params);
        std::string run_id = run.id;

        std::ostringstream detail_ss;
        if (verbose) {
            detail_ss << "Run started: " << run_id << "\n";
        }

        // Step 2: Emit events as training progresses
        int events_emitted = 0;
        for (int epoch = 1; epoch <= 4; ++epoch) {
            drip::EmitEventParams evt;
            evt.run_id = run_id;
            evt.event_type = "training.epoch";
            evt.quantity = 1536;
            evt.units = "tokens";
            evt.cost_units = 1536 * 0.00001;
            evt.metadata["epoch"] = std::to_string(epoch);

            double loss = 2.0 * std::exp(-0.2 * epoch);
            evt.metadata["loss"] = to_string_2f(loss);

            // Unique idempotency key per epoch to avoid dedup
            std::ostringstream idem;
            idem << "incr-epoch-" << run_id << "-" << epoch;
            evt.idempotency_key = idem.str();

            std::ostringstream desc;
            desc << "Epoch " << epoch << ": 1536 tokens, loss=" << to_string_2f(loss);
            evt.description = desc.str();

            auto result = client.emitEvent(evt);
            ++events_emitted;

            if (verbose) {
                detail_ss << "  Event " << epoch << ": " << result.id
                          << (result.is_duplicate ? " (dup)" : "") << "\n";
            }
        }

        // Emit a checkpoint event mid-run
        {
            drip::EmitEventParams ckpt;
            ckpt.run_id = run_id;
            ckpt.event_type = "model.checkpoint";
            ckpt.quantity = 1;
            ckpt.units = "saves";
            ckpt.description = "Mid-training checkpoint";
            ckpt.metadata["checkpoint_path"] = "live/play2train-v1-mid.bin";
            ckpt.idempotency_key = "incr-ckpt-" + run_id;
            client.emitEvent(ckpt);
            ++events_emitted;
        }

        // Step 3: End the run
        drip::EndRunParams end_params;
        end_params.status = drip::RUN_COMPLETED;
        end_params.metadata["final_loss"] = "1.10";
        end_params.metadata["total_epochs"] = "4";

        auto end_result = client.endRun(run_id, end_params);

        if (verbose) {
            detail_ss << "Run ended: duration=" << end_result.duration_ms
                      << "ms, events=" << end_result.event_count << "\n";
        }

        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << "Lifecycle complete: start -> " << events_emitted
            << " events -> end (" << end_result.duration_ms << "ms run)";

        return {6, "Incremental Run API (start/emit/end)", true, dur,
                msg.str(), detail_ss.str()};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {6, "Incremental Run API (start/emit/end)", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 7: Inference / Prediction Metering
//
// After training, models serve predictions. Each inference call on Play2Train
// costs tokens. This simulates a burst of prediction requests from a user,
// metered individually — the core monetization path for a deployed model.
// =============================================================================

static ScenarioResult scenario_inference_metering(drip::Client& client,
                                                  const std::string& customer_id,
                                                  bool verbose) {
    auto start = now_ms();
    try {
        drip::RecordRunParams params;
        params.customer_id = customer_id;
        params.workflow = "glades-inference";
        params.status = drip::RUN_COMPLETED;
        params.metadata["model_name"] = "play2train-ffn-v3";
        params.metadata["model_version"] = "v3.2-epoch9";
        params.metadata["deployment"] = "production";

        int total_predictions = 0;
        int total_tokens = 0;

        // Simulate 20 inference requests of varying sizes
        for (int i = 1; i <= 20; ++i) {
            int input_tokens = 64 + (i * 13) % 200;  // vary input size
            int output_tokens = 32 + (i * 7) % 100;
            int req_tokens = input_tokens + output_tokens;
            total_tokens += req_tokens;
            ++total_predictions;

            drip::RecordRunEvent evt;
            evt.event_type = "inference.prediction";
            evt.quantity = req_tokens;
            evt.units = "tokens";
            evt.cost_units = req_tokens * 0.000005; // cheaper than training
            evt.metadata["request_id"] = "req-" + std::to_string(i);
            evt.metadata["input_tokens"] = std::to_string(input_tokens);
            evt.metadata["output_tokens"] = std::to_string(output_tokens);
            params.events.push_back(evt);
        }

        // Latency summary event
        drip::RecordRunEvent summary;
        summary.event_type = "inference.batch_complete";
        summary.quantity = total_predictions;
        summary.units = "predictions";
        summary.metadata["total_tokens"] = std::to_string(total_tokens);
        summary.metadata["avg_tokens"] = std::to_string(total_tokens / total_predictions);
        summary.description = "Batch of " + std::to_string(total_predictions) + " predictions";
        params.events.push_back(summary);

        auto result = client.recordRun(params);
        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << total_predictions << " predictions, " << total_tokens
            << " tokens, cost=" << result.total_cost_units;

        std::string det;
        if (verbose) {
            std::ostringstream ds;
            ds << "Run ID: " << result.run.id
               << ", Events: " << result.events.created;
            det = ds.str();
        }

        return {7, "Inference / Prediction Metering", true, dur, msg.str(), det};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {7, "Inference / Prediction Metering", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 8: Idempotency / Retry Safety
//
// Network failures happen. When a client retries a trackUsage call, the same
// event must not be double-billed. This sends the same idempotency key twice
// and verifies the second call is recognized as a duplicate.
// =============================================================================

static ScenarioResult scenario_idempotency(drip::Client& client,
                                           const std::string& customer_id,
                                           bool verbose) {
    auto start = now_ms();
    try {
        // Generate a unique idempotency key for this test run
        std::ostringstream idem_ss;
        idem_ss << "idem-test-" << now_ms();
        std::string idem_key = idem_ss.str();

        // First call — should succeed normally
        drip::TrackUsageParams params;
        params.customer_id = customer_id;
        params.meter = "ml_training_tokens";
        params.quantity = 5000;
        params.units = "tokens";
        params.idempotency_key = idem_key;
        params.description = "Idempotency test: first send";
        params.metadata["attempt"] = "1";

        auto result1 = client.trackUsage(params);

        // Second call — same idempotency key, should be deduplicated
        params.metadata["attempt"] = "2";
        params.description = "Idempotency test: retry (should dedup)";

        auto result2 = client.trackUsage(params);

        int dur = static_cast<int>(now_ms() - start);

        // Both should return the same usage_event_id
        bool ids_match = (result1.usage_event_id == result2.usage_event_id);

        std::ostringstream msg;
        msg << "Sent same key twice: IDs "
            << (ids_match ? "match (dedup works)" : "DIFFER (dedup BROKEN!)");

        std::string det;
        if (verbose) {
            std::ostringstream ds;
            ds << "Key: " << idem_key << "\n"
               << "  Call 1: " << result1.usage_event_id << "\n"
               << "  Call 2: " << result2.usage_event_id;
            det = ds.str();
        }

        return {8, "Idempotency / Retry Safety", ids_match, dur, msg.str(), det};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {8, "Idempotency / Retry Safety", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 9: Hyperparameter Sweep
//
// Common ML workflow: grid-search over learning rates and batch sizes.
// Each config gets its own training run. Platform can compare cost vs.
// accuracy across the sweep to find the cheapest good config.
// =============================================================================

static ScenarioResult scenario_hyperparam_sweep(drip::Client& client,
                                                const std::string& customer_id,
                                                bool verbose) {
    auto start = now_ms();
    try {
        double learning_rates[] = {0.1, 0.01, 0.001};
        int batch_sizes[] = {32, 64};
        int total_configs = 0;

        std::ostringstream detail_ss;

        for (int lr_i = 0; lr_i < 3; ++lr_i) {
            for (int bs_i = 0; bs_i < 2; ++bs_i) {
                double lr = learning_rates[lr_i];
                int bs = batch_sizes[bs_i];
                ++total_configs;

                drip::RecordRunParams params;
                params.customer_id = customer_id;
                params.workflow = "glades-hyperparam-sweep";
                params.metadata["sweep_id"] = "sweep-001";
                params.metadata["learning_rate"] = to_string_2f(lr);
                params.metadata["batch_size"] = std::to_string(bs);
                params.metadata["config_index"] = std::to_string(total_configs);

                // Simulate: high LR diverges, low LR converges slowly
                bool diverged = (lr >= 0.1 && bs == 32);
                int epochs = diverged ? 3 : 5;
                params.status = diverged ? drip::RUN_FAILED : drip::RUN_COMPLETED;
                if (diverged) {
                    params.error_message = "Diverged at epoch 3";
                    params.error_code = "DIVERGENCE";
                }

                int tokens_per_epoch = bs * 32;
                for (int e = 1; e <= epochs; ++e) {
                    drip::RecordRunEvent evt;
                    evt.event_type = "training.epoch";
                    evt.quantity = tokens_per_epoch;
                    evt.units = "tokens";
                    evt.cost_units = tokens_per_epoch * 0.00001;
                    evt.metadata["epoch"] = std::to_string(e);
                    params.events.push_back(evt);
                }

                auto result = client.recordRun(params);

                if (verbose) {
                    detail_ss << "  lr=" << to_string_2f(lr)
                              << " bs=" << bs << ": "
                              << (diverged ? "FAILED" : "OK")
                              << " cost=" << result.total_cost_units << "\n";
                }
            }
        }

        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << total_configs << " configs tested (3 LRs x 2 batch sizes), "
            << "1 diverged";

        return {9, "Hyperparameter Sweep", true, dur, msg.str(), detail_ss.str()};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {9, "Hyperparameter Sweep", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Scenario 10: Batch Inference Job
//
// Score an entire dataset through a trained model. One run with many events,
// tracking throughput (predictions/sec) and total cost. This is how Play2Train
// would bill a user for running evaluation on their test set.
// =============================================================================

static ScenarioResult scenario_batch_inference(drip::Client& client,
                                               const std::string& customer_id,
                                               bool verbose) {
    auto start = now_ms();
    try {
        drip::RecordRunParams params;
        params.customer_id = customer_id;
        params.workflow = "glades-batch-inference";
        params.status = drip::RUN_COMPLETED;
        params.metadata["model_name"] = "play2train-ffn-v3.2";
        params.metadata["dataset"] = "user-test-set-2024";
        params.metadata["dataset_size"] = "1000";

        int total_scored = 0;
        int total_tokens = 0;

        // Process in 10 batches of 100
        for (int batch = 1; batch <= 10; ++batch) {
            int items = 100;
            int tokens = items * 128; // 128 tokens avg per item
            total_scored += items;
            total_tokens += tokens;

            drip::RecordRunEvent evt;
            evt.event_type = "inference.batch";
            evt.quantity = tokens;
            evt.units = "tokens";
            evt.cost_units = tokens * 0.000003; // bulk inference discount
            evt.metadata["batch_number"] = std::to_string(batch);
            evt.metadata["items_scored"] = std::to_string(items);
            evt.metadata["accuracy"] = to_string_2f(0.89 + 0.001 * batch);

            std::ostringstream desc;
            desc << "Batch " << batch << "/10: " << items
                 << " items, " << tokens << " tokens";
            evt.description = desc.str();

            params.events.push_back(evt);
        }

        // Final evaluation summary
        drip::RecordRunEvent eval;
        eval.event_type = "inference.evaluation";
        eval.quantity = total_scored;
        eval.units = "predictions";
        eval.description = "Dataset scoring complete";
        eval.metadata["total_items"] = std::to_string(total_scored);
        eval.metadata["total_tokens"] = std::to_string(total_tokens);
        eval.metadata["final_accuracy"] = "0.899";
        eval.metadata["throughput_items_per_sec"] = "250";
        params.events.push_back(eval);

        auto result = client.recordRun(params);
        int dur = static_cast<int>(now_ms() - start);

        std::ostringstream msg;
        msg << total_scored << " items scored in 10 batches, "
            << total_tokens << " tokens, cost=" << result.total_cost_units;

        std::string det;
        if (verbose) {
            std::ostringstream ds;
            ds << "Run ID: " << result.run.id
               << ", Events: " << result.events.created
               << ", Accuracy: 0.899";
            det = ds.str();
        }

        return {10, "Batch Inference Job", true, dur, msg.str(), det};
    } catch (const drip::DripError& e) {
        int dur = static_cast<int>(now_ms() - start);
        return {10, "Batch Inference Job", false, dur,
                std::string("Failed: ") + e.what(), ""};
    }
}

// =============================================================================
// Reporter
// =============================================================================

static void print_scenario(const ScenarioResult& r, bool verbose) {
    const char* icon = r.success ? GREEN : RED;
    const char* status = r.success ? "PASS" : "FAIL";

    std::cout << "  " << icon << "[" << status << "]" << RESET
              << " " << BOLD << "Scenario " << r.number << RESET
              << ": " << r.name
              << DIM << " (" << r.duration_ms << "ms)" << RESET
              << std::endl;

    if (!r.message.empty()) {
        std::cout << "        " << r.message << std::endl;
    }

    if (verbose && !r.details.empty()) {
        // Print details with indentation
        std::istringstream stream(r.details);
        std::string line;
        while (std::getline(stream, line)) {
            if (!line.empty()) {
                std::cout << "        " << DIM << line << RESET << std::endl;
            }
        }
    }
}

// =============================================================================
// Main
// =============================================================================

int main(int argc, char** argv) {
    bool verbose = false;
    int specific_scenario = 0; // 0 = run all

    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--verbose") == 0 || std::strcmp(argv[i], "-v") == 0) {
            verbose = true;
        } else if (std::strcmp(argv[i], "--scenario") == 0 || std::strcmp(argv[i], "-s") == 0) {
            if (i + 1 < argc) {
                specific_scenario = std::atoi(argv[++i]);
            }
        } else if (std::strcmp(argv[i], "--help") == 0 || std::strcmp(argv[i], "-h") == 0) {
            std::cout << "Usage: drip-ml-test [OPTIONS]\n\n"
                      << "ML Training Integration Tests for Drip C++ SDK\n"
                      << "Simulates glades-ml / Play2Train training workflows.\n\n"
                      << "Options:\n"
                      << "  --scenario N, -s N   Run a specific scenario (1-10)\n"
                      << "  --verbose, -v        Show extra details\n"
                      << "  --help, -h           Show this help\n\n"
                      << "Scenarios:\n"
                      << "  1   Multi-epoch training run with token metering\n"
                      << "  2   Checkpoint / state save tracking\n"
                      << "  3   Per-user usage attribution (3 platform users)\n"
                      << "  4   Failed training run (divergence detection)\n"
                      << "  5   Multi-model architecture comparison\n"
                      << "  6   Incremental run API (startRun/emitEvent/endRun)\n"
                      << "  7   Inference / prediction metering (20 requests)\n"
                      << "  8   Idempotency / retry safety (duplicate detection)\n"
                      << "  9   Hyperparameter sweep (6 configs, grid search)\n"
                      << "  10  Batch inference job (1000 items scored)\n";
            return 0;
        }
    }

    std::string customer_id = env_or("TEST_CUSTOMER_ID", "seed-customer-1");

    std::cout << std::endl;
    std::cout << CYAN << BOLD
              << "Drip ML Training Integration Tests v" << DRIP_SDK_VERSION
              << RESET << std::endl;
    std::cout << "Simulating glades-ml / Play2Train training workflows"
              << std::endl;
    std::cout << "==========================================================="
              << std::endl;

    // Initialize client
    drip::Config config;
    std::string api_url = env_or("DRIP_API_URL", "");
    if (!api_url.empty()) {
        if (api_url.size() < 3 || api_url.substr(api_url.size() - 3) != "/v1") {
            api_url += "/v1";
        }
        config.base_url = api_url;
    }

    try {
        drip::Client client(config);

        if (verbose) {
            std::cout << DIM << "  API URL:  "
                      << (config.base_url.empty() ? "(default)" : config.base_url)
                      << RESET << std::endl;
            std::cout << DIM << "  Customer: " << customer_id << RESET << std::endl;
            std::cout << std::endl;
        }

        // Verify connectivity first
        auto health = client.ping();
        if (!health.ok) {
            std::cerr << RED << "API not healthy, aborting tests." << RESET << std::endl;
            return 1;
        }
        std::cout << DIM << "  API connected (" << health.latency_ms << "ms)"
                  << RESET << std::endl;
        std::cout << std::endl;

        // Define all scenarios
        typedef ScenarioResult (*ScenarioFn)(drip::Client&, const std::string&, bool);
        struct Scenario {
            int number;
            ScenarioFn fn;
        };

        Scenario all_scenarios[] = {
            {1, scenario_training_run},
            {2, scenario_checkpoint_tracking},
            {3, scenario_per_user_attribution},
            {4, scenario_failed_training},
            {5, scenario_model_comparison},
            {6, scenario_incremental_run},
            {7, scenario_inference_metering},
            {8, scenario_idempotency},
            {9, scenario_hyperparam_sweep},
            {10, scenario_batch_inference}
        };
        int num_scenarios = 10;

        std::vector<ScenarioResult> results;

        for (int i = 0; i < num_scenarios; ++i) {
            if (specific_scenario > 0 && all_scenarios[i].number != specific_scenario) {
                continue;
            }
            results.push_back(all_scenarios[i].fn(client, customer_id, verbose));
        }

        // Print results
        for (size_t i = 0; i < results.size(); ++i) {
            print_scenario(results[i], verbose);
            if (i + 1 < results.size()) {
                std::cout << std::endl;
            }
        }

        // Summary
        int passed = 0, failed = 0;
        for (size_t i = 0; i < results.size(); ++i) {
            if (results[i].success) ++passed;
            else ++failed;
        }

        std::cout << std::endl;
        std::cout << "==========================================================="
                  << std::endl;

        if (failed == 0) {
            std::cout << GREEN << BOLD << "All " << passed
                      << " scenarios passed." << RESET << std::endl;
        } else {
            std::cout << RED << BOLD << failed << " of " << (passed + failed)
                      << " scenarios failed." << RESET << std::endl;
        }

        std::cout << std::endl;
        return failed > 0 ? 1 : 0;

    } catch (const drip::DripError& e) {
        std::cerr << RED << "FATAL: " << e.what() << RESET << std::endl;
        std::cerr << "Ensure DRIP_API_KEY is set." << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cerr << RED << "FATAL: " << e.what() << RESET << std::endl;
        return 1;
    }
}
