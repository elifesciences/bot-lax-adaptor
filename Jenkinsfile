elifeLibrary {
    stage 'Checkout'
    checkout scm

    stage 'Project tests'
    elifeLocalTests "./project_tests.sh"
    
    elifeMainlineOnly {    
        stage 'Master'
        elifeGitMoveToBranch elifeGitRevision(), 'master'
    }
}
