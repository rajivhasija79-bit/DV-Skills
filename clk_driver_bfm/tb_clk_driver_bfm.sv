// =============================================================================
// Testbench: tb_clk_driver_bfm
// Tests clk_driver_bfm at multiple frequencies, pause/resume, and cycle wait.
// Simulation time unit: 1 ps  (allows sub-nanosecond resolution)
// =============================================================================
`timescale 1ps/1ps

`include "clk_driver_bfm.sv"

module tb_clk_driver_bfm;

    // -------------------------------------------------------------------------
    // Interfaces — one per frequency under test
    // -------------------------------------------------------------------------
    clk_if if_1mhz   ();   //   1 MHz  → period = 1000 ns
    clk_if if_10mhz  ();   //  10 MHz  → period =  100 ns
    clk_if if_100mhz ();   // 100 MHz  → period =   10 ns
    clk_if if_250mhz ();   // 250 MHz  → period =    4 ns
    clk_if if_custom ();   // runtime-parameter example (50 MHz)

    // -------------------------------------------------------------------------
    // BFM instances (parameterised at elaboration time)
    // -------------------------------------------------------------------------
    clk_driver_bfm #(.CLK_FREQ_MHZ(1.0))   bfm_1mhz;
    clk_driver_bfm #(.CLK_FREQ_MHZ(10.0))  bfm_10mhz;
    clk_driver_bfm #(.CLK_FREQ_MHZ(100.0)) bfm_100mhz;
    clk_driver_bfm #(.CLK_FREQ_MHZ(250.0)) bfm_250mhz;
    clk_driver_bfm #(.CLK_FREQ_MHZ(50.0))  bfm_custom;

    // -------------------------------------------------------------------------
    // Pass/fail counters
    // -------------------------------------------------------------------------
    int pass_count = 0;
    int fail_count = 0;

    // -------------------------------------------------------------------------
    // Helper: check measured frequency is within tolerance
    // -------------------------------------------------------------------------
    task automatic check_freq(
        string       name,
        real         target_mhz,
        longint      cycles,
        real         elapsed_ns,
        real         tol_pct = 0.5   // ±0.5 % default tolerance
    );
        real measured_mhz, err_pct;
        if (elapsed_ns <= 0) begin
            $display("FAIL [%s] elapsed_ns is zero — no clock activity", name);
            fail_count++;
            return;
        end
        measured_mhz = (real'(cycles) / elapsed_ns) * 1000.0;
        err_pct      = ((measured_mhz - target_mhz) / target_mhz) * 100.0;
        if (err_pct < 0) err_pct = -err_pct;   // abs

        if (err_pct <= tol_pct) begin
            $display("PASS [%s] target=%.2f MHz  measured=%.4f MHz  err=%.4f%%",
                     name, target_mhz, measured_mhz, err_pct);
            pass_count++;
        end else begin
            $display("FAIL [%s] target=%.2f MHz  measured=%.4f MHz  err=%.4f%% > tol=%.1f%%",
                     name, target_mhz, measured_mhz, err_pct, tol_pct);
            fail_count++;
        end
    endtask

    // -------------------------------------------------------------------------
    // TEST 1 — Basic frequency accuracy for each BFM
    // -------------------------------------------------------------------------
    task test_frequency_accuracy();
        int unsigned RUN_CYCLES = 100;
        $display("\n=== TEST 1: Frequency Accuracy (%0d cycles each) ===", RUN_CYCLES);

        fork
            bfm_1mhz.run();
            bfm_10mhz.run();
            bfm_100mhz.run();
            bfm_250mhz.run();
            bfm_custom.run();

            // Stop each BFM after RUN_CYCLES rising edges
            begin
                bfm_1mhz.wait_cycles(RUN_CYCLES);   bfm_1mhz.stop();
            end
            begin
                bfm_10mhz.wait_cycles(RUN_CYCLES);  bfm_10mhz.stop();
            end
            begin
                bfm_100mhz.wait_cycles(RUN_CYCLES); bfm_100mhz.stop();
            end
            begin
                bfm_250mhz.wait_cycles(RUN_CYCLES); bfm_250mhz.stop();
            end
            begin
                bfm_custom.wait_cycles(RUN_CYCLES);  bfm_custom.stop();
            end
        join

        check_freq("1 MHz",    1.0,   bfm_1mhz.clk_count,   bfm_1mhz.elapsed_ns);
        check_freq("10 MHz",   10.0,  bfm_10mhz.clk_count,  bfm_10mhz.elapsed_ns);
        check_freq("100 MHz",  100.0, bfm_100mhz.clk_count, bfm_100mhz.elapsed_ns);
        check_freq("250 MHz",  250.0, bfm_250mhz.clk_count, bfm_250mhz.elapsed_ns);
        check_freq("50 MHz",   50.0,  bfm_custom.clk_count,  bfm_custom.elapsed_ns);
    endtask

    // -------------------------------------------------------------------------
    // TEST 2 — Pause and resume (clock count must not advance while paused)
    // -------------------------------------------------------------------------
    task test_pause_resume();
        clk_driver_bfm #(.CLK_FREQ_MHZ(100.0)) bfm_pr;
        clk_if if_pr ();   // local interface
        longint cnt_before, cnt_after_pause, cnt_after_resume;

        $display("\n=== TEST 2: Pause / Resume ===");
        bfm_pr = new(if_pr);

        fork
            bfm_pr.run();
            begin
                bfm_pr.wait_cycles(20);
                cnt_before = bfm_pr.clk_count;

                bfm_pr.pause_clk();
                #500000;                          // wait 500 ns in sim time
                cnt_after_pause = bfm_pr.clk_count;

                if (cnt_before == cnt_after_pause) begin
                    $display("PASS [pause] clock halted at %0d cycles", cnt_before);
                    pass_count++;
                end else begin
                    $display("FAIL [pause] clock advanced during pause: %0d → %0d",
                             cnt_before, cnt_after_pause);
                    fail_count++;
                end

                bfm_pr.resume_clk();
                bfm_pr.wait_cycles(10);
                cnt_after_resume = bfm_pr.clk_count;

                if (cnt_after_resume >= cnt_after_pause + 10) begin
                    $display("PASS [resume] clock restarted, cycles now %0d", cnt_after_resume);
                    pass_count++;
                end else begin
                    $display("FAIL [resume] expected ≥%0d cycles, got %0d",
                             cnt_after_pause + 10, cnt_after_resume);
                    fail_count++;
                end

                bfm_pr.stop();
            end
        join
    endtask

    // -------------------------------------------------------------------------
    // TEST 3 — wait_cycles accuracy (wall-clock check)
    // -------------------------------------------------------------------------
    task test_wait_cycles();
        clk_driver_bfm #(.CLK_FREQ_MHZ(100.0)) bfm_wc;
        clk_if if_wc ();
        time t_start, t_end;
        real expected_ps, actual_ps, err_pct;
        int  WAIT_N = 50;

        $display("\n=== TEST 3: wait_cycles Timing (%0d cycles @ 100 MHz) ===", WAIT_N);
        bfm_wc = new(if_wc);
        expected_ps = WAIT_N * 10_000.0;   // 50 × 10 ns = 500 ns = 500 000 ps

        fork
            bfm_wc.run();
            begin
                t_start = $time;
                bfm_wc.wait_cycles(WAIT_N);
                t_end   = $time;
                bfm_wc.stop();

                actual_ps = real'(t_end - t_start);
                err_pct   = ((actual_ps - expected_ps) / expected_ps) * 100.0;
                if (err_pct < 0) err_pct = -err_pct;

                if (err_pct <= 1.0) begin
                    $display("PASS [wait_cycles] expected=%.0f ps  actual=%.0f ps  err=%.3f%%",
                             expected_ps, actual_ps, err_pct);
                    pass_count++;
                end else begin
                    $display("FAIL [wait_cycles] expected=%.0f ps  actual=%.0f ps  err=%.3f%%",
                             expected_ps, actual_ps, err_pct);
                    fail_count++;
                end
            end
        join
    endtask

    // -------------------------------------------------------------------------
    // TEST 4 — Duty cycle (50/50 check via posedge/negedge timing)
    // -------------------------------------------------------------------------
    task test_duty_cycle();
        clk_driver_bfm #(.CLK_FREQ_MHZ(200.0)) bfm_dc;
        clk_if if_dc ();
        time t_rise, t_fall;
        real high_time_ps, low_time_ps, duty_pct;

        $display("\n=== TEST 4: Duty Cycle (200 MHz) ===");
        bfm_dc = new(if_dc);

        fork
            bfm_dc.run();
            begin
                @(posedge if_dc.clk); t_rise = $time;
                @(negedge if_dc.clk); t_fall = $time;
                @(posedge if_dc.clk);

                high_time_ps = real'(t_fall - t_rise);
                low_time_ps  = real'($time   - t_fall);
                duty_pct     = (high_time_ps / (high_time_ps + low_time_ps)) * 100.0;

                if (duty_pct >= 49.0 && duty_pct <= 51.0) begin
                    $display("PASS [duty_cycle] high=%.0f ps  low=%.0f ps  duty=%.2f%%",
                             high_time_ps, low_time_ps, duty_pct);
                    pass_count++;
                end else begin
                    $display("FAIL [duty_cycle] duty=%.2f%%  (expected 50%%)", duty_pct);
                    fail_count++;
                end

                bfm_dc.stop();
            end
        join
    endtask

    // -------------------------------------------------------------------------
    // Main test sequence
    // -------------------------------------------------------------------------
    initial begin
        $display("============================================================");
        $display("  Clock Driver BFM Testbench");
        $display("============================================================");

        // Construct BFMs
        bfm_1mhz   = new(if_1mhz);
        bfm_10mhz  = new(if_10mhz);
        bfm_100mhz = new(if_100mhz);
        bfm_250mhz = new(if_250mhz);
        bfm_custom = new(if_custom);

        // Run tests sequentially
        test_frequency_accuracy();
        test_pause_resume();
        test_wait_cycles();
        test_duty_cycle();

        // Summary
        $display("\n============================================================");
        $display("  Results: %0d PASSED  |  %0d FAILED", pass_count, fail_count);
        $display("============================================================");
        if (fail_count == 0)
            $display("  ALL TESTS PASSED");
        else
            $display("  SOME TESTS FAILED — review output above");

        $finish;
    end

    // Safety watchdog — kill sim if it hangs
    initial begin
        #100_000_000;   // 100 ms sim time
        $display("ERROR: simulation watchdog expired");
        $finish(1);
    end

endmodule
