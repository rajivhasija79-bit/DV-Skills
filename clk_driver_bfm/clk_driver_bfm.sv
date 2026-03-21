// Clock Driver BFM Class
// Generates clock at any frequency defined by parameter (in MHz)

class clk_driver_bfm #(real CLK_FREQ_MHZ = 100.0);

    // Derived timing
    real   period_ns;
    real   half_period_ns;

    // Clock signal reference (virtual interface or logic ref)
    virtual clk_if vif;

    // Control flags
    bit    running;
    bit    enable;

    // Statistics
    longint unsigned clk_count;
    real             elapsed_ns;

    // Constructor
    function new(virtual clk_if vif_in);
        this.vif           = vif_in;
        this.period_ns     = 1000.0 / CLK_FREQ_MHZ;   // ns per cycle
        this.half_period_ns = period_ns / 2.0;
        this.running       = 0;
        this.enable        = 1;
        this.clk_count     = 0;
        this.elapsed_ns    = 0.0;
    endfunction

    // Start clock generation (blocking — call in a fork)
    task run();
        running    = 1;
        vif.clk    = 0;
        clk_count  = 0;
        elapsed_ns = 0.0;

        $display("[CLK_BFM] Starting clock: %.2f MHz  period=%.3f ns  half=%.3f ns",
                 CLK_FREQ_MHZ, period_ns, half_period_ns);

        while (running) begin
            if (enable) begin
                #(half_period_ns * 1ns / 1ns);   // scale to simulation time unit (1 ps default)
                vif.clk    = ~vif.clk;
                if (vif.clk == 1) begin           // count on rising edge
                    clk_count++;
                    elapsed_ns += period_ns;
                end
            end else begin
                @(enable);                        // wait until re-enabled
            end
        end
    endtask

    // Stop clock generation
    function void stop();
        running = 0;
        $display("[CLK_BFM] Stopped after %0d cycles  (%.3f ns elapsed)", clk_count, elapsed_ns);
    endfunction

    // Pause / resume without stopping the task
    function void pause_clk();  enable = 0; endfunction
    function void resume_clk(); enable = 1; endfunction

    // Wait for N rising edges
    task wait_cycles(int unsigned n);
        repeat (n) @(posedge vif.clk);
    endtask

    // Report measured frequency based on elapsed sim time
    function void report();
        real measured_mhz;
        if (elapsed_ns > 0)
            measured_mhz = (real'(clk_count) / elapsed_ns) * 1000.0;
        else
            measured_mhz = 0.0;
        $display("[CLK_BFM] Report — target: %.2f MHz | measured: %.4f MHz | cycles: %0d",
                 CLK_FREQ_MHZ, measured_mhz, clk_count);
    endfunction

endclass
