eval $(ssh-agent)
ssh-add /home/expadmin/.ssh/GitHub
git add .
git commit -m "Initial Commit" --amend
git push --force
