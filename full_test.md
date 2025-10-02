# Full Test Checklist - Rivvy Create LLMs.txt System

## 🎯 System Overview
This checklist covers the complete end-to-end testing of the Rivvy Create LLMs.txt system, including web scraping, file generation, ElevenLabs integration, and GitHub Actions workflow.

---

## 📋 Pre-Test Setup Verification

### ✅ System Status Check
- [ ] **ElevenLabs Knowledge Base**: 37 documents uploaded with proper filenames
- [ ] **Agent Assignment**: All documents assigned to `agent_3001k6fy77ytfj7t3jbcwn21ag16`
- [ ] **Sync State**: Clean and up-to-date in `config/elevenlabs_sync_state.json`
- [ ] **Git Status**: All changes committed and pushed to main branch
- [ ] **Observer Monitoring**: All 27 collection URLs added with 24-hour intervals

### ✅ Configuration Verification
- [ ] **Site Config**: `config/site_configs.json` contains `jgengineering.ie` configuration
- [ ] **Agent Config**: `config/elevenlabs-agents.json` has correct agent ID
- [ ] **API Keys**: All required API keys present in `env.local`
- [ ] **File Structure**: 37 shard files present in `out/jgengineering-ie/`

---

## 🧪 Test Scenarios

### Test 1: Product Addition Workflow
**Objective**: Verify that adding a new product to a monitored collection triggers the complete workflow.

#### Steps:
1. **Add Test Product**
   - [ ] Navigate to: `https://www.jgengineering.ie/collections/ba-helicoil-kits-ireland`
   - [ ] Add a new test product (e.g., `test_workflow_verification`)
   - [ ] Ensure product is visible on the collection page

2. **Observer Detection**
   - [ ] Wait for observer to detect change (within 24 hours)
   - [ ] Check GitHub Actions for new webhook trigger
   - [ ] Verify webhook payload contains correct domain and change type

3. **GitHub Actions Processing**
   - [ ] Confirm workflow starts successfully
   - [ ] Check that diff extraction finds the new product URL
   - [ ] Verify Firecrawl scraping completes without timeout
   - [ ] Confirm shard file is updated with new product

4. **ElevenLabs Sync**
   - [ ] Verify old document is unassigned from agent
   - [ ] Confirm old document is deleted from ElevenLabs
   - [ ] Check new document is uploaded with proper filename
   - [ ] Verify new document is assigned to agent
   - [ ] Confirm sync state is updated and committed

5. **Verification**
   - [ ] Check ElevenLabs dashboard shows updated document
   - [ ] Verify document name matches filename (not content-based)
   - [ ] Confirm agent has correct document count
   - [ ] Test RAG functionality with new product

#### Expected Results:
- ✅ New product appears in shard file
- ✅ ElevenLabs document is replaced (not duplicated)
- ✅ Document has proper filename
- ✅ Agent assignment is correct
- ✅ Sync state is committed to git

---

### Test 2: Product Removal Workflow
**Objective**: Verify that removing a product from a monitored collection triggers the complete workflow.

#### Steps:
1. **Remove Test Product**
   - [ ] Navigate to: `https://www.jgengineering.ie/collections/ba-helicoil-kits-ireland`
   - [ ] Remove the test product added in Test 1
   - [ ] Ensure product is no longer visible on collection page

2. **Observer Detection**
   - [ ] Wait for observer to detect change (within 24 hours)
   - [ ] Check GitHub Actions for new webhook trigger
   - [ ] Verify webhook payload contains correct domain and change type

3. **GitHub Actions Processing**
   - [ ] Confirm workflow starts successfully
   - [ ] Check that diff extraction finds the removed product URL
   - [ ] Verify shard file is updated without the removed product
   - [ ] Confirm file hash changes to trigger ElevenLabs replacement

4. **ElevenLabs Sync**
   - [ ] Verify old document is unassigned from agent
   - [ ] Confirm old document is deleted from ElevenLabs
   - [ ] Check new document is uploaded with proper filename
   - [ ] Verify new document is assigned to agent
   - [ ] Confirm sync state is updated and committed

5. **Verification**
   - [ ] Check ElevenLabs dashboard shows updated document
   - [ ] Verify removed product is no longer in document content
   - [ ] Confirm agent has correct document count
   - [ ] Test RAG functionality without removed product

#### Expected Results:
- ✅ Removed product no longer appears in shard file
- ✅ ElevenLabs document is replaced (not duplicated)
- ✅ Document has proper filename
- ✅ Agent assignment is correct
- ✅ Sync state is committed to git

---

### Test 3: Multiple Product Changes
**Objective**: Verify system handles multiple product additions/removals in a single change.

#### Steps:
1. **Multiple Changes**
   - [ ] Add 2-3 new test products to a collection
   - [ ] Remove 1-2 existing products from the same collection
   - [ ] Ensure all changes are visible on collection page

2. **Observer Detection**
   - [ ] Wait for observer to detect change (within 24 hours)
   - [ ] Check GitHub Actions for new webhook trigger
   - [ ] Verify webhook payload contains all changes

3. **GitHub Actions Processing**
   - [ ] Confirm workflow processes all changes
   - [ ] Check that diff extraction finds all added/removed products
   - [ ] Verify shard file reflects all changes correctly

4. **ElevenLabs Sync**
   - [ ] Verify document replacement handles multiple changes
   - [ ] Confirm final document contains all expected products
   - [ ] Check sync state is updated correctly

5. **Verification**
   - [ ] Verify all changes are reflected in final document
   - [ ] Test RAG functionality with updated product list

#### Expected Results:
- ✅ All product changes are processed correctly
- ✅ Single document replacement handles multiple changes
- ✅ Final document is accurate and complete

---

### Test 4: Error Handling & Recovery
**Objective**: Verify system handles errors gracefully and recovers properly.

#### Steps:
1. **Firecrawl Timeout Simulation**
   - [ ] Add a product to a collection
   - [ ] Monitor for Firecrawl timeout errors
   - [ ] Verify system retries with exponential backoff
   - [ ] Check that workflow completes successfully on retry

2. **ElevenLabs API Errors**
   - [ ] Monitor for any ElevenLabs API failures
   - [ ] Verify error handling and logging
   - [ ] Check that sync state remains consistent

3. **Git Conflicts**
   - [ ] Simulate concurrent changes
   - [ ] Verify git conflict resolution
   - [ ] Check that sync state is properly merged

#### Expected Results:
- ✅ System retries failed operations
- ✅ Errors are logged appropriately
- ✅ System recovers and completes successfully
- ✅ Sync state remains consistent

---

### Test 5: Cross-Site Agnostic Testing
**Objective**: Verify system works correctly across different website structures.

#### Steps:
1. **Different Site Configuration**
   - [ ] Test with a different site in `site_configs.json`
   - [ ] Verify URL pattern matching works correctly
   - [ ] Check that product extraction is agnostic

2. **Different Product URL Structures**
   - [ ] Test with sites using different product URL patterns
   - [ ] Verify diff extraction works with various patterns
   - [ ] Check that shard organization is correct

#### Expected Results:
- ✅ System adapts to different site structures
- ✅ URL patterns are correctly identified
- ✅ Product extraction works across sites

---

## 🔍 Monitoring & Verification

### GitHub Actions Monitoring
- [ ] **Webhook Triggers**: Monitor for `website_changed` events
- [ ] **Workflow Execution**: Check for successful workflow runs
- [ ] **Error Logs**: Review any failed runs and error messages
- [ ] **Sync State Commits**: Verify sync state is committed after each run

### ElevenLabs Monitoring
- [ ] **Document Count**: Verify correct number of documents
- [ ] **Document Names**: Check that filenames are preserved
- [ ] **Agent Assignment**: Confirm all documents are assigned
- [ ] **RAG Indexing**: Verify documents are indexed for RAG

### File System Monitoring
- [ ] **Shard Files**: Check that shard files are updated correctly
- [ ] **Manifest Files**: Verify manifest reflects current state
- [ ] **Sync State**: Confirm sync state matches ElevenLabs state

---

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

#### Issue: Firecrawl Timeout
**Symptoms**: Workflow fails with timeout errors
**Solution**: 
- Check Firecrawl API status
- Verify retry logic is working
- Consider increasing timeout values

#### Issue: ElevenLabs Sync Failures
**Symptoms**: Documents not uploaded or assigned
**Solution**:
- Check API key validity
- Verify agent configuration
- Review sync state consistency

#### Issue: Git Conflicts
**Symptoms**: Push failures due to conflicts
**Solution**:
- Pull latest changes
- Resolve conflicts manually
- Ensure sync state is consistent

#### Issue: Observer Not Detecting Changes
**Symptoms**: No webhook triggers
**Solution**:
- Check observer configuration
- Verify collection URLs are monitored
- Review observer logs

---

## 📊 Success Criteria

### ✅ Complete Success
- [ ] All test scenarios pass without errors
- [ ] ElevenLabs documents have proper filenames
- [ ] Agent assignments are correct
- [ ] Sync state is consistent
- [ ] RAG functionality works correctly
- [ ] System handles errors gracefully

### ⚠️ Partial Success
- [ ] Core functionality works
- [ ] Minor issues with error handling
- [ ] Some edge cases need attention

### ❌ Failure
- [ ] Core functionality broken
- [ ] ElevenLabs sync issues
- [ ] File generation problems
- [ ] Observer detection failures

---

## 📝 Test Results Log

### Test Execution Log
```
Date: ___________
Tester: ___________
Environment: ___________

Test 1 - Product Addition:
[ ] Pass [ ] Fail [ ] Partial
Notes: _________________________________

Test 2 - Product Removal:
[ ] Pass [ ] Fail [ ] Partial
Notes: _________________________________

Test 3 - Multiple Changes:
[ ] Pass [ ] Fail [ ] Partial
Notes: _________________________________

Test 4 - Error Handling:
[ ] Pass [ ] Fail [ ] Partial
Notes: _________________________________

Test 5 - Cross-Site Testing:
[ ] Pass [ ] Fail [ ] Partial
Notes: _________________________________

Overall Result: [ ] Success [ ] Partial [ ] Failure
```

---

## 🎯 Next Steps After Testing

### If All Tests Pass:
1. **Production Deployment**: System is ready for production use
2. **Monitoring Setup**: Implement ongoing monitoring
3. **Documentation**: Update user documentation
4. **Training**: Train users on system usage

### If Tests Fail:
1. **Issue Analysis**: Identify root causes
2. **Fix Implementation**: Address identified issues
3. **Re-testing**: Re-run failed test scenarios
4. **Iteration**: Continue until all tests pass

### If Partial Success:
1. **Priority Assessment**: Determine which issues to fix first
2. **Incremental Fixes**: Address issues one by one
3. **Re-testing**: Verify fixes work correctly
4. **Documentation**: Document known limitations

---

*This checklist should be used for comprehensive testing of the Rivvy Create LLMs.txt system. Each test scenario should be executed thoroughly to ensure system reliability and functionality.*
