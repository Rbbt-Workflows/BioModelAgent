"""Scout-level test for the MaBoSS Tier 2 python tasks (plan Step 5).

Mirrors ``test_neko_python_tasks_tier2.rb`` and adds the plan's acceptance
test 4 (single-path chaining through the Ruby harness):

- registration of the simulation/plotting task family;
- ``task_info`` exposes inputs and ``Extension:`` metadata;
- a three-task chain runs through ``job().run(true)`` where every hop
  consumes the previous hop's single returned path:
  ``maboss_bnet_to_bnd_cfg`` → ``maboss_set_output_nodes`` →
  ``maboss_update_parameters`` → ``maboss_run_simulation``.

Run from the repository root: ``ruby test/BioModelAgent/tasks/test_maboss_python_tasks_tier2.rb``
"""

require File.expand_path('../../test_helper', __dir__)
require File.expand_path('../../../workflow.rb', __dir__)
require 'tmpdir'

class TestMabossPythonTasksTier2 < Test::Unit::TestCase

  TINY_BNET = "targets, factors\nA, B\nB, A\nC, A & B\n".freeze

  TIER2 = %w[
    maboss_change_rule
    maboss_update_parameters
    maboss_set_output_nodes
    maboss_set_initial_state
    maboss_run_simulation
    maboss_simulate_mutation
    maboss_plot_trajectories
  ].freeze

  def test_all_tier2_tasks_registered
    TIER2.each do |name|
      assert(BioModelAgent.tasks.key?(name.to_sym),
             "task #{name} is not registered in BioModelAgent")
    end
    assert_equal(32, BioModelAgent.tasks.length,
                 'total task count must stay 32 (17 NeKo + 15 MaBoSS-family)')
  end

  def test_tier2_task_metadata_extracted
    TIER2.each do |name|
      info = BioModelAgent.task_info(name.to_sym)
      inputs = info[:inputs]
      assert(!inputs.empty?, "task #{name} exposes no inputs")
      names = inputs.map { |i| i.is_a?(Hash) ? i[:name].to_s : i.to_s }
      assert(names.include?('bundle'),
             "task #{name} lacks a bundle input: #{names.inspect}")
      assert(info[:extension], "task #{name} lacks an 'Extension:' line")
      assert(!info[:description].to_s.strip.empty?,
             "task #{name} produced an empty description")
    end
  end

  def test_chained_tasks_share_one_path
    Dir.mktmpdir do |tmp|
      bnet = File.join(tmp, 'tiny.bnet')
      File.write(bnet, TINY_BNET)

      hop = lambda do |name, inputs|
        job = BioModelAgent.job(name, inputs)
        job.run(true)
        job.load.to_s
      end

      # Hop 1: BNET -> bundle directory.
      bundle = hop.call(:maboss_bnet_to_bnd_cfg, :bnet_path => bnet)
      assert(File.directory?(bundle), "hop 1: #{bundle} is not a directory")

      # Hop 2: bundle -> bundle with a small output set (2^N warning).
      with_outputs = hop.call(:maboss_set_output_nodes,
                              :bundle => bundle, :nodes => 'A,B')
      assert(File.directory?(with_outputs))
      assert_not_equal(bundle, with_outputs, 'config task must return a NEW bundle')

      # Hop 3: bundle -> bundle with explicit small time parameters.
      runnable = hop.call(:maboss_update_parameters,
                          :bundle => with_outputs,
                          :parameters => 'max_time=10,time_tick=1')
      assert(File.directory?(runnable))

      # Hop 4: bundle -> numeric probtraj TSV.
      tsv = hop.call(:maboss_run_simulation, :bundle => runnable)
      assert(File.file?(tsv))
      lines = File.readlines(tsv)
      assert(lines.first.start_with?('#'),
             "scout TSV header expected: #{lines.first.inspect}")
      assert(lines.length < 100,
             "explicit max_time=10 must keep the TSV small, got #{lines.length}")

      # Hop 5: bundle -> PNG.
      png = hop.call(:maboss_plot_trajectories, :bundle => runnable, :until => 10)
      assert(File.file?(png))
      assert_equal("\x89PNG\r\n\x1a\n".b, File.open(png, 'rb') { |f| f.read(8) },
                   'plot artifact lacks PNG magic bytes')

      # Hop 6: bundle -> WT/mutant comparison TSV.
      mut = hop.call(:maboss_simulate_mutation,
                     :bundle => runnable, :nodes => 'C', :state => 'OFF')
      assert(File.file?(mut))
      header = File.readlines(mut).first.strip.split("\t")
      assert(header.include?('variant'), "mutation TSV lacks a variant column")
      first_column = File.readlines(mut)[1..].map { |l| l.split("\t").first }
      %w[wild-type mutant].each do |variant|
        assert(first_column.include?(variant),
               "#{variant} row missing from #{File.basename(mut)}")
      end

      # Acceptance test 7, Scout-side: the hop-1 input bundle must still hold
      # both members after four downstream tasks consumed it.
      assert(File.file?(File.join(bundle, 'model.bnd')))
      assert(File.file?(File.join(bundle, 'model.cfg')))
    end
  end
end
