require File.expand_path('../../test_helper', __dir__)
require File.expand_path('../../../workflow.rb', __dir__)

# Scout-side paired test for the Tier 1 NeKo python tasks (plan Step 6).
# (a) registration: the 8 Tier 1 tasks exist in the BioModelAgent workflow;
# (b) metadata: scout-rig runs each task file as a subprocess when the task
#     is described, so any syntax or import error in a task file surfaces as
#     a task-level error here; extension and input defaults come from the
#     parsed docstring/annotations;
# (c) functional: python/test/test_tier1.py must pass under the pymaboss
#     python (the interpreter that has neko installed).
class TestNekoPythonTasksTier1 < Test::Unit::TestCase
  PY = ENV['NEKO_PYTHON'] || '/home/mvazque2/software/micromamba/envs/pymaboss/bin/python'
  REPO = File.expand_path('../../..', __dir__)

  TIER1 = %w[
    neko_create_sif neko_add_nodes neko_remove_genes neko_remove_interaction
    neko_remove_bimodal_interactions neko_network_report
    neko_list_interactions neko_find_paths
  ].freeze

  def test_python_tasks_registered
    TIER1.each do |name|
      assert BioModelAgent.tasks.include?(name.to_sym),
             "task #{name} not registered in BioModelAgent"
    end
  end

  def test_python_task_metadata_loads
    TIER1.each do |name|
      info = BioModelAgent.task_info(name.to_sym)
      assert !info[:description].to_s.empty?,
             "task #{name} produced an empty description"
      assert info[:extension],
             "task #{name} docstring lacks an 'Extension:' line"
    end
  end

  def test_python_test_suite_runs
    suite = File.join(REPO, 'python', 'test', 'test_tier1.py')
    assert File.exist?(suite), "missing #{suite}"
    out = %x{cd #{REPO.shellescape} && timeout 500 #{PY} #{suite.shellescape} 2>&1}
    assert $?.success?, "python/test/test_tier1.py failed:\n#{out[-2000..] || out}"
  end
end
