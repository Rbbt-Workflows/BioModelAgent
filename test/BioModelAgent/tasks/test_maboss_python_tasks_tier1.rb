"""Scout-level test for the MaBoSS Tier 1 python tasks (plan Step 5).

Mirrors ``test_neko_python_tasks_tier1.rb``:

- the workflow loads and every MaBoSS task is registered;
- ``--scout-metadata`` exposes the documented inputs and the ``Extension:``
  line for each task;
- one task runs end-to-end through the Ruby ``job().run(true)`` harness.

Run from the repository root: ``ruby test/BioModelAgent/tasks/test_maboss_python_tasks_tier1.rb``
"""

require File.expand_path('../../test_helper', __dir__)
require File.expand_path('../../../workflow.rb', __dir__)
require 'tmpdir'

class TestMabossPythonTasksTier1 < Test::Unit::TestCase

  TINY_BNET = "targets, factors\nA, B\nB, A\nC, A & B\n".freeze
  INSPECTION_TASKS = %w[
    maboss_bnet_to_bnd_cfg
    maboss_list_nodes
    maboss_get_initial_state
    maboss_get_logical_rules
    maboss_get_mutations
    maboss_get_parameters
    maboss_check
    neko_export_bnet
  ].freeze

  def test_workflow_loads_with_maboss_tasks
    assert_equal(32, BioModelAgent.tasks.length,
                 'workflow must register 17 NeKo + 15 MaBoSS-family tasks')
    INSPECTION_TASKS.each do |name|
      assert(BioModelAgent.tasks.include?(name),
             "#{name} missing from BioModelAgent.tasks")
    end
  end

  def test_maboss_task_metadata_documents_inputs_and_extension
    INSPECTION_TASKS.each do |name|
      info = BioModelAgent.task_info(name.to_sym)
      assert !info[:description].to_s.empty?,
             "task #{name} produced an empty description"
      assert(info[:extension], "task #{name} lacks an 'Extension:' line")
      raw_inputs = info[:inputs] || []
      inputs = raw_inputs.map { |i| i.is_a?(Hash) ? i[:name].to_s : i.to_s }
      assert(inputs.any? { |i| %w[bundle bnet_path sif_path].include?(i) },
             "task #{name} does not take a path input: #{inputs.inspect}")
    end
  end

  def test_bnet_to_bundle_runs_through_scout_harness
    Dir.mktmpdir do |tmp|
      bnet = File.join(tmp, 'tiny.bnet')
      File.write(bnet, TINY_BNET)

      job = BioModelAgent.job(:maboss_bnet_to_bnd_cfg, :bnet_path => bnet)
      job.run(true)
      bundle = job.load.to_s
      assert_not_nil(bundle, 'task must return one path (the bundle dir)')
      assert(File.directory?(bundle), "returned path #{bundle} is not a dir")
      assert(File.file?(File.join(bundle, 'model.bnd')))
      assert(File.file?(File.join(bundle, 'model.cfg')))

      # The very next task consumes the same single path (single-path chaining).
      inspect = BioModelAgent.job(:maboss_list_nodes, :bundle => bundle)
      inspect.run(true)
      tsv = inspect.load.to_s
      assert(File.file?(tsv))
      header = File.readlines(tsv).first
      assert(header.start_with?('#node'),
             "scout TSV header expected, got: #{header.inspect}")
    end
  end
end
